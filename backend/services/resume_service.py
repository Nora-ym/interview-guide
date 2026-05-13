"""
====================================================
简历服务（修复版）
====================================================

修复了以下问题：

【1. 分析永远卡住 —— 最核心问题】
  原问题：analyze_resume 的 except 块末尾有 raise，异常被重新抛出
          → Celery 的 autoretry_for=(Exception,) 触发重试
          → 3 次重试耗尽后任务失败，但 status 可能卡在 "analyzing"；
          如果 Celery Worker 根本没启动，status 永远是 "pending"。
  修复：  ① except 块不再 raise，analysis_status 正确落地为 "failed"
          ② 对外暴露 run_analysis_inline() 供 API 层在 Celery 不可用时
             直接在 FastAPI BackgroundTasks 里执行，无需 Worker 也能分析
          ③ 加 asyncio.wait_for 超时（120s），防止 AI 接口挂死

【2. 空简历被分析】
  原问题：parsed_text 解析失败时为 None，
          直接把空字符串发给 AI，浪费调用且结果无意义。
  修复：  parsed_text 为空时直接设 failed，附带明确的错误信息。

【3. 无法重新分析】
  新增：  reset_for_reanalysis() 把状态重置为 pending，
          供 POST /resumes/{id}/reanalyze 接口调用。
"""

import asyncio
import io
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.resume import Resume
from backend.models.user import User
from backend.utils.document_parser import DocumentParser
from backend.utils.pdf_generator import generate_resume_analysis_pdf
from backend.services.storage_service import upload_file, delete_file
from backend.services.ai_service import chat_structured


# ================================================================
# 上传简历
# ================================================================

async def upload_resume(
    db: AsyncSession,
    user: User,
    file_data: bytes,
    filename: str,
    content_type: str,
) -> Resume:
    """
    上传简历（同步立即返回，分析由外部触发）。
    返回的 Resume 对象 analysis_status = "pending"。
    """
    file_url = upload_file(
        file_data, filename,
        folder="resumes",
        content_type=content_type,
    )

    content_hash = DocumentParser.compute_hash(io.BytesIO(file_data))

    # 去重检查
    existing = await db.execute(
        select(Resume).where(
            Resume.user_id == user.id,
            Resume.content_hash == content_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("已存在相同内容的简历")

    # 解析文本（失败不阻断上传）
    try:
        parsed_text = DocumentParser.parse(io.BytesIO(file_data), filename)
    except Exception:
        parsed_text = None

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


# ================================================================
# 分析简历（Celery Worker 版本）
# ================================================================

async def analyze_resume(resume_id: int) -> dict:
    """
    AI 分析简历（给 Celery Worker 调用，同步 DB 上下文）。

    修复要点：
    - except 块不再 raise，让 Celery 认为任务已完成（无论成败）
      失败信息通过 analysis_status="failed" + analysis_result 传递
    - 加 asyncio.wait_for 超时，防止 AI 接口无限挂死
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.config import get_settings

    engine = create_engine(get_settings().database_url_sync)

    with Session(engine) as db:
        resume = db.get(Resume, resume_id)
        if not resume:
            # 记录不存在，直接返回，不 raise（避免无意义重试）
            return {"status": "not_found", "resume_id": resume_id}

        # 检查是否已分析完成（防止重复执行）
        if resume.analysis_status == "completed":
            return {"status": "already_completed", "resume_id": resume_id}

        resume.analysis_status = "analyzing"
        db.commit()

        try:
            # parsed_text 为空直接报错，不浪费 AI 调用
            if not resume.parsed_text or not resume.parsed_text.strip():
                raise ValueError(
                    "简历文本解析失败或内容为空，请检查文件格式是否支持"
                    "（支持 PDF、DOCX、TXT、MD、PPTX）"
                )

            # 加超时保护，防止 AI 接口挂死（120秒）
            analysis = await asyncio.wait_for(
                _call_ai_analysis(resume.parsed_text),
                timeout=120,
            )

            resume.analysis_status = "completed"
            resume.analysis_result = analysis

            # 生成 PDF 报告
            try:
                pdf_bytes = generate_resume_analysis_pdf(
                    analysis, resume.title, ""
                )
                resume.report_url = upload_file(
                    pdf_bytes,
                    f"resume_report_{resume.id}.pdf",
                    folder="reports",
                    content_type="application/pdf",
                )
            except Exception as pdf_err:
                # PDF 生成失败不影响分析结果
                pass

            db.commit()
            return {"status": "completed", "resume_id": resume_id}

        except asyncio.TimeoutError:
            resume.analysis_status = "failed"
            resume.analysis_result = {
                "error": "AI 分析超时（超过 120 秒），请稍后重试"
            }
            db.commit()
            # 不 raise：让 Celery 认为任务正常完成，避免无意义重试
            return {"status": "timeout", "resume_id": resume_id}

        except Exception as e:
            resume.analysis_status = "failed"
            resume.analysis_result = {"error": str(e)}
            db.commit()
            # 不 raise：状态已落地为 failed，重试没有意义
            return {"status": "failed", "resume_id": resume_id, "error": str(e)}


# ================================================================
# 分析简历（FastAPI BackgroundTasks 版本）
# ================================================================

async def run_analysis_inline(resume_id: int, db: AsyncSession) -> None:
    """
    在 FastAPI 进程内异步执行简历分析（无需 Celery Worker）。

    适用场景：
    - 开发环境没有启动 Celery Worker
    - Celery / Redis 连接失败时的兜底

    注意：使用异步 DB Session（与 Celery 版本的同步 Session 不同）。
    进程重启会丢失正在执行的任务，生产环境建议用 Celery。
    """
    # 重新查询确保拿到最新状态
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        return
    if resume.analysis_status == "completed":
        return

    resume.analysis_status = "analyzing"
    await db.flush()
    await db.commit()

    # 重新获取 session（commit 后原 session 内对象已过期）
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        return

    try:
        if not resume.parsed_text or not resume.parsed_text.strip():
            raise ValueError(
                "简历文本解析失败或内容为空，"
                "请检查文件格式（支持 PDF、DOCX、TXT、MD、PPTX）"
            )

        analysis = await asyncio.wait_for(
            _call_ai_analysis(resume.parsed_text),
            timeout=120,
        )

        resume.analysis_status = "completed"
        resume.analysis_result = analysis

        try:
            pdf_bytes = generate_resume_analysis_pdf(
                analysis, resume.title, ""
            )
            resume.report_url = upload_file(
                pdf_bytes,
                f"resume_report_{resume.id}.pdf",
                folder="reports",
                content_type="application/pdf",
            )
        except Exception:
            pass

        await db.commit()

    except asyncio.TimeoutError:
        resume.analysis_status = "failed"
        resume.analysis_result = {
            "error": "AI 分析超时（超过 120 秒），请稍后重试"
        }
        await db.commit()

    except Exception as e:
        resume.analysis_status = "failed"
        resume.analysis_result = {"error": str(e)}
        await db.commit()


# ================================================================
# 重置状态（供重新分析接口使用）
# ================================================================

async def reset_for_reanalysis(
    db: AsyncSession, resume_id: int, user_id: int
) -> Resume | None:
    """
    把简历状态重置为 pending，以便触发重新分析。
    仅允许操作自己的简历。
    """
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        return None

    resume.analysis_status = "pending"
    resume.analysis_result = None
    resume.task_id = None
    await db.flush()
    await db.refresh(resume)
    return resume


# ================================================================
# AI 分析核心（内部函数）
# ================================================================

async def _call_ai_analysis(parsed_text: str) -> dict:
    """
    调用 AI 分析简历内容。

    返回标准化的分析结果字典。
    score 字段使用整数 0 占位，防止 AI 返回字符串导致后续处理出错。
    """
    system_prompt = (
        "你是一位资深招聘技术面试官和简历评估专家。"
        "请仔细阅读简历内容，给出客观专业的评估。\n"
        "评分要求：\n"
        "- overall_score 必须是 0-100 之间的整数\n"
        "- 内容充实、经验丰富：70-90 分\n"
        "- 内容一般、有明显缺失：40-70 分\n"
        "- 内容很少或无实质信息：0-40 分\n"
        "- 评分必须基于简历实际内容，不能给出与内容质量明显不符的分数"
    )

    schema = {
        "overall_score": 0,
        "strengths": ["优势1", "优势2"],
        "weaknesses": ["不足1", "不足2"],
        "skill_tags": ["技能1", "技能2"],
        "position_match": "适合的岗位方向",
        "improvement_suggestions": ["建议1", "建议2", "建议3"],
        "summary": "总体评价（2-3句）",
    }

    result = await chat_structured(
        messages=[{
            "role": "user",
            "content": (
                f"请分析以下简历内容：\n\n{parsed_text}\n\n"
                "注意：overall_score 必须是整数，不能带'分'字或其他文字。"
            )
        }],
        output_schema=schema,
        temperature=0.3,
        system_prompt=system_prompt,
    )

    # 类型安全：确保 overall_score 是整数
    raw_score = result.get("overall_score", 0)
    try:
        score = int(float(str(raw_score).replace("分", "").strip()))
        score = max(0, min(100, score))
    except (ValueError, TypeError):
        score = 0
    result["overall_score"] = score

    # 确保 list 字段不为 None
    for key in ["strengths", "weaknesses", "skill_tags", "improvement_suggestions"]:
        if not isinstance(result.get(key), list):
            result[key] = []

    return result


# ================================================================
# 查询接口
# ================================================================

async def get_user_resumes(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Resume], int]:
    """获取用户的简历列表（分页），返回 (列表, 总数)"""
    query = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
    )
    count_query = (
        select(func.count())
        .select_from(Resume)
        .where(Resume.user_id == user_id)
    )
    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_resume(
    db: AsyncSession, resume_id: int, user_id: int
) -> Resume | None:
    """获取单个简历（同时验证归属权）"""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_resume(
    db: AsyncSession, resume_id: int, user_id: int
) -> bool:
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