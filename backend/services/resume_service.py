"""
简历服务
处理简历相关的业务逻辑：

上传简历：保存文件 + 解析文本 + 创建记录
AI 分析简历：调用大模型评估简历质量
查询/删除简历
异步处理说明：
简历 AI 分析可能需要 10-30 秒，不能让用户等着页面转圈。
所以：上传后立即返回 → Celery 在后台分析 → 前端轮询进度
"""

import io
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.resume import Resume
from backend.models.user import User
from backend.utils.document_parser import DocumentParser
from backend.utils.pdf_generator import generate_resume_analysis_pdf
from backend.services.storage_service import upload_file, delete_file
from backend.services.ai_service import chat_structured


async def upload_resume(
    db: AsyncSession,
    user: User,
    file_data: bytes,
    filename: str,
    content_type: str,
) -> Resume:
    """
    上传简历（同步，立即返回）

    流程：
    1. 把文件存到存储系统
    2. 计算文件内容哈希（去重）
    3. 解析文件内容为纯文本
    4. 在数据库中创建简历记录（状态为 pending）

    调用方（API 路由）拿到返回值后触发 Celery 异步任务进行 AI 分析
    """
    # 第一步：存储文件
    file_url = upload_file(
        file_data, filename,
        folder="resumes",
        content_type=content_type,
    )

    # 第二步：计算哈希（用于去重）
    content_hash = DocumentParser.compute_hash(io.BytesIO(file_data))

    # 检查是否已存在相同内容的简历
    existing = await db.execute(
        select(Resume).where(
            Resume.user_id == user.id,
            Resume.content_hash == content_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("已存在相同内容的简历")

    # 第三步：解析文本
    try:
        parsed_text = DocumentParser.parse(io.BytesIO(file_data), filename)
    except Exception:
        parsed_text = None

    # 第四步：创建数据库记录
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    resume = Resume(
        user_id=user.id,
        title=filename.rsplit(".", 1)[0] if "." in filename else filename,
        file_url=file_url,
        file_type=ext,
        file_size=len(file_data),
        content_hash=content_hash,
        parsed_text=parsed_text,
        analysis_status="pending",
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)
    return resume


async def analyze_resume(resume_id: int) -> dict:
    """
    AI 分析简历（给 Celery Worker 调用）

    注意：Celery Worker 是同步环境，不能直接用 async/await。
    所以内部用同步方式连接数据库（pymysql 而不是 aiomysql）。

    流程：
    1. 从数据库取出简历
    2. 调用 AI 分析简历内容
    3. 生成 PDF 报告
    4. 更新数据库
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.config import get_settings

    engine = create_engine(get_settings().database_url_sync)

    with Session(engine) as db:
        resume = db.get(Resume, resume_id)
        if not resume:
            raise ValueError(f"简历不存在: {resume_id}")

        resume.analysis_status = "analyzing"
        db.commit()

        try:
            # 调用 AI 分析
            analysis = await _call_ai_analysis(resume.parsed_text or "")
            resume.analysis_status = "completed"
            resume.analysis_result = analysis

            # 生成 PDF 报告
            pdf_bytes = generate_resume_analysis_pdf(analysis, resume.title, "")
            report_url = upload_file(
                pdf_bytes,
                f"resume_report_{resume.id}.pdf",
                folder="reports",
                content_type="application/pdf",
            )
            resume.report_url = report_url
            db.commit()
            return {"status": "completed", "resume_id": resume_id}

        except Exception as e:
            resume.analysis_status = "failed"
            resume.analysis_result = {"error": str(e)}
            db.commit()
            raise


async def _call_ai_analysis(parsed_text: str) -> dict:
    """调用 AI 分析简历内容（内部函数）"""
    system_prompt = """你是资深招聘技术面试官和简历评估专家。请分析简历，给出评估。
要求：综合评分0-100、至少3个优势、至少2个不足、技能标签、岗位匹配建议、至少3条改进建议、总体评价"""

    schema = {
        "overall_score": 85,
        "strengths": ["优势1", "优势2", "优势3"],
        "weaknesses": ["不足1", "不足2"],
        "skill_tags": ["Java", "Spring Boot", "MySQL"],
        "position_match": "适合中高级后端开发",
        "improvement_suggestions": ["建议1", "建议2", "建议3"],
        "summary": "总体评价文字...",
    }

    return await chat_structured(
        messages=[{"role": "user", "content": f"请分析以下简历：\n\n{parsed_text}"}],
        output_schema=schema,
        temperature=0.3,
        system_prompt=system_prompt,
    )


async def get_user_resumes(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 20,
) -> tuple[list[Resume], int]:
    """获取用户的简历列表（分页），返回 (列表, 总数)"""
    query = select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    count_query = select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().all()), total or 0


async def get_resume(db: AsyncSession, resume_id: int, user_id: int) -> Resume | None:
    """获取单个简历（同时验证归属权）"""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_resume(db: AsyncSession, resume_id: int, user_id: int) -> bool:
    """删除简历（同时删除存储的文件）"""
    resume = await get_resume(db, resume_id, user_id)
    if not resume:
        return False
    await db.delete(resume)
    await db.flush()
    try:
        if resume.file_url:
            delete_file(resume.file_url)
        if resume.report_url:
            delete_file(resume.report_url)
    except Exception:
        pass
    return True