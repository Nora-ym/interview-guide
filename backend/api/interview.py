"""
====================================================
模拟面试 API（文字面试）
====================================================
接口列表：
    GET  /interviews/skills           - 获取可用技能方向
    POST /interviews                   - 创建面试
    GET  /interviews                   - 面试列表
    GET  /interviews/active            - 获取进行中的面试
    GET  /interviews/{id}              - 面试详情（含消息）
    POST /interviews/{id}/answer       - 提交回答
    POST /interviews/{id}/end          - 手动结束面试
    GET  /interviews/{id}/report       - 下载评估报告
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.user import User
from backend.models.interview import Interview
from backend.schemas.common import ApiResponse, PageResult
from backend.schemas.interview import InterviewCreate, InterviewOut, InterviewAnswer
from backend.dependencies import get_current_user
from backend.services import interview_service
from backend.services.storage_service import get_presigned_url

router = APIRouter()


@router.get("/skills")
async def list_skills():
    """获取所有可用的技能方向（前端展示选择列表用）"""
    return ApiResponse(data=interview_service.get_available_skills())


@router.post("")
async def create_interview(
    body: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    创建面试
    请求体：{"skill_id": "java_backend", "difficulty": "medium", "interview_type": "text"}
    返回：面试详情（含 AI 的开场白 + 第一题）
    """
    # 如果已有进行中的面试，直接返回它（避免重复创建）
    existing = await db.execute(select(Interview).where(
        and_(Interview.user_id == user.id,
             Interview.status == "in_progress",
             Interview.interview_type == body.interview_type)))
    ongoing = existing.scalar_one_or_none()
    if ongoing:
        return ApiResponse(data=InterviewOut.model_validate(ongoing), message="已有进行中的面试")

    # 创建面试会话
    interview = await interview_service.create_interview(
        db, user, body.skill_id, body.difficulty, body.interview_type, body.max_rounds)

    # 开始面试（AI 发出开场白 + 第一题）
    await interview_service.start_interview(db, interview)
    await db.refresh(interview)

    return ApiResponse(data=InterviewOut.model_validate(interview))


@router.get("")
async def list_interviews(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """面试列表（可选按状态筛选）"""
    interviews, total = await interview_service.get_user_interviews(
        db, user.id, status, page, page_size)
    return ApiResponse(data=PageResult(
        total=total, page=page, page_size=page_size,
        items=[InterviewOut.model_validate(i) for i in interviews],
    ))


@router.get("/active")
async def get_active(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前进行中的文字面试（前端用来判断是否需要创建新面试）"""
    result = await db.execute(select(Interview).where(
        and_(Interview.user_id == user.id,
             Interview.status == "in_progress",
             Interview.interview_type == "text")))
    interview = result.scalar_one_or_none()
    if not interview:
        return ApiResponse(data=None, message="没有进行中的面试")
    return ApiResponse(data=InterviewOut.model_validate(interview))


@router.get("/{interview_id}")
async def get_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """面试详情（含所有消息）"""
    interview = await interview_service.get_interview_detail(db, interview_id, user.id)
    if not interview:
        raise HTTPException(status_code=404, detail="面试不存在")
    return ApiResponse(data=InterviewOut.model_validate(interview))


@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: int,
    body: InterviewAnswer,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    提交回答
    请求体：{"content": "Spring Boot 通过自动配置减少了手动配置..."}
    返回：AI 的回复 + 是否结束
    """
    interview = await interview_service.get_interview_detail(db, interview_id, user.id)
    if not interview:
        raise HTTPException(status_code=404, detail="面试不存在")
    try:
        response = await interview_service.submit_answer(db, interview, body.content)
        await db.refresh(interview)
        return ApiResponse(data={
            "response": response,
            "status": interview.status,
            "current_round": interview.current_round,
            "is_finished": interview.status == "completed",
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{interview_id}/end")
async def end_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动结束面试（不等达到最大轮数）"""
    interview = await interview_service.get_interview_detail(db, interview_id, user.id)
    if not interview:
        raise HTTPException(status_code=404, detail="面试不存在")
    if interview.status != "in_progress":
        raise HTTPException(status_code=400, detail="面试已结束")
    conclusion = await interview_service.finish_interview(db, interview)
    await db.refresh(interview)
    return ApiResponse(data={
        "evaluation": interview.evaluation,
        "total_score": interview.total_score,
        "conclusion": conclusion,
    })


@router.get("/{interview_id}/report")
async def download_report(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取评估报告的下载链接"""
    interview = await interview_service.get_interview_detail(db, interview_id, user.id)
    if not interview:
        raise HTTPException(status_code=404, detail="面试不存在")
    if not interview.report_url:
        raise HTTPException(status_code=400, detail="报告尚未生成")
    return ApiResponse(data={"download_url": get_presigned_url(interview.report_url)})
