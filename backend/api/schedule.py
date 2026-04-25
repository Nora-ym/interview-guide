
"""
====================================================
面试安排 API
====================================================
接口列表：
    POST   /schedules/parse           - AI 解析邀请文本
    POST   /schedules                 - 手动创建安排
    POST   /schedules/from-text       - 从文本创建（解析+创建一步到位）
    GET    /schedules                 - 安排列表（分页+筛选）
    GET    /schedules/calendar        - 日历数据（按月获取事件）
    GET    /schedules/{id}            - 安排详情
    PUT    /schedules/{id}            - 更新安排
    DELETE /schedules/{id}            - 删除安排
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.user import User
from backend.models.schedule import InterviewSchedule
from backend.schemas.common import ApiResponse, PageResult
from backend.schemas.schedule import (
    ScheduleCreate, ScheduleParseRequest, ScheduleOut, ScheduleUpdate,
)
from backend.dependencies import get_current_user
from backend.services import schedule_service

router = APIRouter()


@router.post("/parse")
async def parse_invite(
    body: ScheduleParseRequest,
    user: User = Depends(get_current_user),
):
    """AI 解析面试邀请文本（只解析不保存）"""
    return ApiResponse(data=await schedule_service.parse_invite(body.text))


@router.post("")
async def create(
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动创建面试安排"""
    schedule = await schedule_service.create_schedule(
        db, user, body.model_dump(exclude_none=True))
    return ApiResponse(data=ScheduleOut.model_validate(schedule))


@router.post("/from-text")
async def create_from_text(
    body: ScheduleParseRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从文本创建（解析+创建一步到位）"""
    parsed = await schedule_service.parse_invite(body.text)
    if "interview_time" not in parsed:
        raise HTTPException(status_code=400, detail="无法从文本中提取面试时间")
    schedule = await schedule_service.create_schedule(
        db, user, parsed, raw_text=body.text)
    return ApiResponse(data=ScheduleOut.model_validate(schedule))


@router.get("")
async def list_schedules(
    status: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """面试安排列表（可按状态和时间范围筛选）"""
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    schedules, total = await schedule_service.get_user_schedules(
        db, user.id, status, start_dt, end_dt, page, page_size)
    return ApiResponse(data=PageResult(
        total=total, page=page, page_size=page_size,
        items=[ScheduleOut.model_validate(s) for s in schedules],
    ))


@router.get("/calendar")
async def calendar_data(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    日历数据（按月获取事件）
    返回格式符合 react-big-calendar 的事件格式
    """
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    schedules, _ = await schedule_service.get_user_schedules(
        db, user.id, None, start, end, 1, 200)

    # 颜色映射：不同状态不同颜色
    colors = {
        "upcoming": "#3B82F6",    # 蓝色
        "completed": "#10B981",   # 绿色
        "cancelled": "#EF4444",   # 红色
    }

    events = [{
        "id": s.id,
        "title": f"{s.company or '面试'} - {s.position or ''}",
        "start": s.interview_time.isoformat(),
        "end": (s.interview_time + timedelta(minutes=s.duration_minutes)).isoformat(),
        "status": s.status,
        "color": colors.get(s.status, "#6B7280"),
    } for s in schedules]

    return ApiResponse(data=events)


@router.get("/{sid}")
async def get_schedule(
    sid: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """面试安排详情"""
    result = await db.execute(select(InterviewSchedule).where(
        InterviewSchedule.id == sid, InterviewSchedule.user_id == user.id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="面试安排不存在")
    return ApiResponse(data=ScheduleOut.model_validate(schedule))


@router.put("/{sid}")
async def update_schedule(
    sid: int,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新面试安排（只传要修改的字段）"""
    schedule = await schedule_service.update_schedule(
        db, sid, user.id, body.model_dump(exclude_none=True))
    if not schedule:
        raise HTTPException(status_code=404, detail="面试安排不存在")
    return ApiResponse(data=ScheduleOut.model_validate(schedule))


@router.delete("/{sid}")
async def delete_schedule(
    sid: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除面试安排"""
    if not await schedule_service.delete_schedule(db, sid, user.id):
        raise HTTPException(status_code=404, detail="面试安排不存在")
    return ApiResponse(message="删除成功")
