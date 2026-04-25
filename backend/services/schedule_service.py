"""
面试安排服务
处理面试安排的业务逻辑：

邀请文本解析（正则 + AI 双引擎）
CRUD 操作
定时过期检查
"""

import re
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.schedule import InterviewSchedule
from backend.models.user import User
from backend.services.ai_service import chat_structured

# 会议链接正则表达式
MEETING_PATTERNS = [
    {"name": "飞书", "pattern": r"https?://(?:vc.feishu|meeting.larksuite).cn/j/(\w+)", "platform": "飞书"},
    {"name": "腾讯会议", "pattern": r"https?://meeting.tencent.com/dm/r/(\w+)", "platform": "腾讯会议"},
    {"name": "Zoom", "pattern": r"https?://(?:[\w.-]+.)*zoom.us/j/(\d+)", "platform": "Zoom"},
]


def parse_meeting_link(text: str) -> dict:
    """用正则提取会议链接信息"""
    result = {"platform": None, "meeting_link": None, "meeting_id": None}
    for p in MEETING_PATTERNS:
        match = re.search(p["pattern"], text)
        if match:
            result["platform"] = p["name"]
            result["meeting_id"] = match.group(1)
            link_match = re.search(r'https?://[^\s<>"\']+', text)
            if link_match:
                result["meeting_link"] = link_match.group(0)
            break
    return result


async def parse_invite(text: str) -> dict:
    """双引擎解析面试邀请：正则提取会议信息 + AI 提取完整信息"""
    meeting = parse_meeting_link(text)
    schema = {
        "company": "", "position": "", "interview_type": "",
        "interview_time": "2025-01-15 14:00", "duration_minutes": 60,
        "interviewer_name": "", "location": "", "notes": "",
        "meeting_platform": "", "meeting_link": "",
    }
    ai_result = await chat_structured(
        messages=[{"role": "user", "content": text}],
        output_schema=schema, temperature=0.1,
        system_prompt="从面试邀请文本中提取结构化信息，interview_time 格式 YYYY-MM-DD HH:MM，无法提取填 null。",
    )
    return {k: v for k, v in {
        "company": ai_result.get("company"),
        "position": ai_result.get("position"),
        "interview_type": ai_result.get("interview_type"),
        "interview_time": ai_result.get("interview_time"),
        "duration_minutes": ai_result.get("duration_minutes", 60),
        "interviewer_name": ai_result.get("interviewer_name"),
        "location": ai_result.get("location"),
        "notes": ai_result.get("notes"),
        "meeting_platform": meeting["platform"] or ai_result.get("meeting_platform"),
        "meeting_link": meeting["meeting_link"] or ai_result.get("meeting_link"),
        "meeting_id": meeting["meeting_id"],
    }.items() if v is not None}


async def create_schedule(
    db: AsyncSession, user: User, data: dict, raw_text: str | None = None,
) -> InterviewSchedule:
    """创建面试安排"""
    it = data.get("interview_time")
    if isinstance(it, str):
        it = datetime.fromisoformat(it)
    schedule = InterviewSchedule(
        user_id=user.id, company=data.get("company"), position=data.get("position"),
        interview_type=data.get("interview_type"), interview_time=it,
        duration_minutes=data.get("duration_minutes", 60),
        meeting_platform=data.get("meeting_platform"),
        meeting_link=data.get("meeting_link"), meeting_id=data.get("meeting_id"),
        location=data.get("location"), interviewer_name=data.get("interviewer_name"),
        notes=data.get("notes"), raw_text=raw_text,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)
    return schedule


async def get_user_schedules(
    db: AsyncSession, user_id: int, status: str | None = None,
    start_date: datetime | None = None, end_date: datetime | None = None,
    page: int = 1, page_size: int = 20,
) -> tuple[list[InterviewSchedule], int]:
    """获取用户的面试安排（分页，可按状态和时间范围筛选）"""
    conditions = [InterviewSchedule.user_id == user_id]
    if status:
        conditions.append(InterviewSchedule.status == status)
    if start_date:
        conditions.append(InterviewSchedule.interview_time >= start_date)
    if end_date:
        conditions.append(InterviewSchedule.interview_time <= end_date)
    query = select(InterviewSchedule).where(and_(*conditions))
    count_query = select(func.count()).select_from(InterviewSchedule).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(InterviewSchedule.interview_time)
        .offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total or 0


async def update_schedule(
    db: AsyncSession, schedule_id: int, user_id: int, data: dict,
) -> InterviewSchedule | None:
    """更新面试安排"""
    result = await db.execute(
        select(InterviewSchedule).where(
            InterviewSchedule.id == schedule_id, InterviewSchedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        return None
    for key, value in data.items():
        if value is not None and hasattr(schedule, key):
            if key == "interview_time" and isinstance(value, str):
                value = datetime.fromisoformat(value)
            setattr(schedule, key, value)
    await db.flush()
    await db.refresh(schedule)
    return schedule


async def delete_schedule(db: AsyncSession, schedule_id: int, user_id: int) -> bool:
    """删除面试安排"""
    result = await db.execute(
        select(InterviewSchedule).where(
            InterviewSchedule.id == schedule_id, InterviewSchedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        return False
    await db.delete(schedule)
    await db.flush()
    return True


async def auto_expire_schedules() -> int:
    """定时任务：把时间已过的 upcoming 状态改为 completed"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.config import get_settings
    engine = create_engine(get_settings().database_url_sync)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        result = db.execute(
            select(InterviewSchedule).where(
                InterviewSchedule.status == "upcoming",
                InterviewSchedule.interview_time < now,
            )
        )
        expired = result.scalars().all()
        for s in expired:
            s.status = "completed"
        db.commit()
        return len(expired)