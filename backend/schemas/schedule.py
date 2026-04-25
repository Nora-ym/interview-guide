"""面试安排相关 Schema"""
from datetime import datetime
from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    """手动创建面试安排请求"""
    company: str | None = None
    position: str | None = None
    interview_type: str | None = None
    interview_time: datetime = Field(description="面试时间")
    duration_minutes: int = 60
    meeting_platform: str | None = None
    meeting_link: str | None = None
    location: str | None = None
    interviewer_name: str | None = None
    notes: str | None = None


class ScheduleParseRequest(BaseModel):
    """AI 解析面试邀请请求"""
    text: str = Field(min_length=1, description="面试邀请文本/链接")


class ScheduleOut(BaseModel):
    """面试安排输出"""
    id: int
    company: str | None = None
    position: str | None = None
    interview_type: str | None = None
    interview_time: datetime
    duration_minutes: int
    meeting_platform: str | None = None
    meeting_link: str | None = None
    meeting_id: str | None = None
    status: str
    location: str | None = None
    interviewer_name: str | None = None
    notes: str | None = None
    reminder_sent: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ScheduleUpdate(BaseModel):
    """更新面试安排请求（所有字段都是可选的，只传要改的）"""
    company: str | None = None
    position: str | None = None
    interview_type: str | None = None
    interview_time: datetime | None = None
    duration_minutes: int | None = None
    meeting_platform: str | None = None
    meeting_link: str | None = None
    location: str | None = None
    interviewer_name: str | None = None
    notes: str | None = None
    status: str | None = None
