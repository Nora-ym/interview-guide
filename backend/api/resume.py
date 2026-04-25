"""
====================================================
简历管理 API
====================================================
接口列表：
    POST   /resumes/upload        - 上传简历
    GET    /resumes                - 简历列表（分页）
    GET    /resumes/{id}           - 简历详情
    GET    /resumes/{id}/status    - 查询分析状态（前端轮询用）
    DELETE /resumes/{id}           - 删除简历
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.user import User
from backend.schemas.common import ApiResponse, PageResult
from backend.schemas.resume import ResumeOut
from backend.dependencies import get_current_user
from backend.services import resume_service
from backend.tasks.resume_tasks import analyze_resume

router = APIRouter()


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),  # File(...) 表示这是一个文件上传参数
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    上传简历

    流程：
    1. 读取上传的文件数据
    2. 检查文件大小（不超过 10MB）
    3. 调用 resume_service 存储文件 + 创建记录
    4. 触发 Celery 异步任务进行 AI 分析
    5. 立即返回（不等待分析完成）
    """
    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    resume = await resume_service.upload_resume(
        db, user, file_data,
        file.filename or "unknown",
        file.content_type or "application/octet-stream",
    )

    # 触发 Celery 异步任务
    task = analyze_resume.delay(resume.id)
    resume.task_id = task.id  # 把任务 ID 存到数据库（前端可以用来查进度）
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
    resumes, total = await resume_service.get_user_resumes(db, user.id, page, page_size)
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
    查询分析状态（前端轮询用）
    前端每隔 3 秒请求一次，直到 status 变为 completed 或 failed
    """
    resume = await resume_service.get_resume(db, resume_id, user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    return ApiResponse(data={
        "resume_id": resume_id,
        "status": resume.analysis_status,
        "task_id": resume.task_id,
        "result": resume.analysis_result,
        "report_url": resume.report_url,
    })


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
