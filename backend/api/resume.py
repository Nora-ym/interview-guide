"""
====================================================
简历管理 API（修复版）
====================================================

修复：
1. 上传后优先用 Celery 触发分析；Celery/Redis 不可用时
   自动降级为 FastAPI BackgroundTasks 在进程内执行分析，
   开发环境不启动 Worker 也能正常分析。
2. 新增 POST /resumes/{id}/reanalyze 接口：
   把状态重置为 pending 并重新触发分析，
   供前端在分析失败或卡住时手动重试。
3. GET /resumes/{id}/status 返回更多调试信息（error 字段）。

接口列表：
    POST   /resumes/upload           - 上传简历
    GET    /resumes                  - 简历列表（分页）
    GET    /resumes/{id}             - 简历详情
    GET    /resumes/{id}/status      - 查询分析状态（前端轮询用）
    POST   /resumes/{id}/reanalyze   - 重新触发分析（新增）
    DELETE /resumes/{id}             - 删除简历
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.schemas.common import ApiResponse, PageResult
from backend.schemas.resume import ResumeOut
from backend.dependencies import get_current_user
from backend.services import resume_service

router = APIRouter()


def _trigger_analysis(
    resume_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> str | None:
    """
    触发简历分析。

    优先使用 Celery（生产环境，有 Worker 的情况）。
    Celery/Redis 不可用时自动降级为 FastAPI BackgroundTasks
    在当前进程内异步执行，开发环境无需启动 Worker 也能正常分析。

    返回：task_id（Celery 模式）或 None（BackgroundTasks 模式）
    """
    try:
        from backend.tasks.resume_tasks import analyze_resume as celery_task
        task = celery_task.delay(resume_id)
        return task.id
    except Exception:
        # Celery/Redis 不可用，降级为 BackgroundTasks
        background_tasks.add_task(resume_service.run_analysis_inline, resume_id, db)
        return None


@router.post("/upload")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    上传简历。

    流程：
    1. 读取文件、校验大小
    2. 调用 resume_service 存储文件 + 创建记录
    3. 触发分析（Celery 优先，不可用时降级为 BackgroundTasks）
    4. 立即返回（不等待分析完成）
    """
    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    try:
        resume = await resume_service.upload_resume(
            db, user, file_data,
            file.filename or "unknown",
            file.content_type or "application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 触发分析（Celery 优先，失败自动降级）
    task_id = _trigger_analysis(resume.id, background_tasks, db)
    if task_id:
        resume.task_id = task_id
        await db.flush()
        await db.refresh(resume)

    return ApiResponse(data=ResumeOut.model_validate(resume))


@router.get("")
async def list_resumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """简历列表（分页）"""
    resumes, total = await resume_service.get_user_resumes(
        db, user.id, page, page_size
    )
    return ApiResponse(data=PageResult(
        total=total, page=page, page_size=page_size,
        items=[ResumeOut.model_validate(r) for r in resumes],
    ))


@router.get("/{resume_id}")
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """简历详情"""
    resume = await resume_service.get_resume(db, resume_id, user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    return ApiResponse(data=ResumeOut.model_validate(resume))


@router.get("/{resume_id}/status")
async def get_status(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    查询分析状态（前端轮询用）。
    前端每隔 3 秒请求一次，直到 status 变为 completed 或 failed。

    返回字段说明：
        status:     pending / analyzing / completed / failed
        result:     分析结果（completed 时有值）
        error:      错误信息（failed 时有值，方便排查）
        report_url: PDF 报告路径（completed 且已生成时有值）
    """
    resume = await resume_service.get_resume(db, resume_id, user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 提取错误信息（failed 时 analysis_result = {"error": "..."}）
    error_msg = None
    if resume.analysis_status == "failed" and isinstance(resume.analysis_result, dict):
        error_msg = resume.analysis_result.get("error")

    return ApiResponse(data={
        "resume_id": resume_id,
        "status": resume.analysis_status,
        "task_id": resume.task_id,
        "result": resume.analysis_result,
        "report_url": resume.report_url,
        "error": error_msg,
    })


@router.post("/{resume_id}/reanalyze")
async def reanalyze(
    resume_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    重新触发简历分析。

    适用场景：
    - 分析状态卡在 pending/analyzing（Celery Worker 未启动导致）
    - 分析失败（AI 接口超时、API Key 错误等）
    - 用户手动要求重新分析

    流程：重置状态为 pending → 重新触发分析（Celery 优先）
    """
    resume = await resume_service.reset_for_reanalysis(db, resume_id, user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    task_id = _trigger_analysis(resume.id, background_tasks, db)
    if task_id:
        resume.task_id = task_id
        await db.flush()
        await db.refresh(resume)

    return ApiResponse(
        data=ResumeOut.model_validate(resume),
        message="已重新触发分析，请稍后刷新状态",
    )


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除简历（同时删除存储的文件）"""
    if not await resume_service.delete_resume(db, resume_id, user.id):
        raise HTTPException(status_code=404, detail="简历不存在")
    return ApiResponse(message="删除成功")