"""
====================================================
面试安排模型
====================================================
对应数据库中的 interview_schedules 表。
管理用户的真实面试安排（不是模拟面试），包括时间、地点、会议链接等。
"""

from datetime import datetime
from sqlalchemy import (
    String, Integer, Text, Boolean, DateTime, ForeignKey, JSON, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, TimestampMixin


class InterviewSchedule(Base, TimestampMixin):
    """
    面试安排模型

    用户可以：
    1. 手动填写面试信息
    2. 粘贴面试邀请邮件/短信 → AI 自动解析出结构化信息
    """
    __tablename__ = "interview_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # ---- 面试信息 ----
    company: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )  # 公司名称
    position: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )  # 岗位名称
    interview_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # 面试轮次：一面/二面/技术面/HR 面/终面
    interview_time: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False
    )  # 面试时间
    duration_minutes: Mapped[int] = mapped_column(
        Integer, default=60
    )  # 预计时长（分钟）

    # ---- 会议信息 ----
    meeting_platform: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # 会议平台：飞书/腾讯会议/Zoom/钉钉
    meeting_link: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # 会议链接
    meeting_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # 会议号

    # ---- 状态和其他 ----
    status: Mapped[str] = mapped_column(
        String(32), default="upcoming"
    )  # 状态：upcoming / completed / cancelled
    location: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )  # 面试地点（线下面试用）
    interviewer_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # 面试官姓名
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 用户备注
    raw_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 原始邀请文本（保留原文，方便回看）
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # 是否已发送提醒

    user: Mapped["User"] = relationship(back_populates="schedules")
