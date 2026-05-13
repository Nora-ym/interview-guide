"""面试相关 Schema"""
from datetime import datetime
from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    """创建面试请求"""
    skill_id: str = Field(description="技能方向标识，如 java_backend")
    difficulty: str = Field(default="medium", description="难度：easy/medium/hard")
    interview_type: str = Field(default="text", description="类型：text/voice")
    max_rounds: int = Field(default=10, ge=1, le=30, description="最大轮数，1-30")


class InterviewMessageOut(BaseModel):
    """面试消息输出"""
    id: int
    role: str           # interviewer 或 candidate
    content: str        # 消息内容
    message_type: str   # text 或 audio
    round: int          # 第几轮
    created_at: datetime
    model_config = {"from_attributes": True}


class InterviewOut(BaseModel):
    """面试会话输出"""
    id: int
    skill_id: str
    skill_name: str
    difficulty: str
    interview_type: str
    status: str
    current_round: int
    max_rounds: int
    total_score: float | None = None
    evaluation: dict | None = None
    report_url: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime | None = None
    messages: list[InterviewMessageOut] = []
    model_config = {"from_attributes": True}


class InterviewAnswer(BaseModel):
    """用户回答请求"""
    content: str = Field(min_length=1, description="回答内容，不能为空")
