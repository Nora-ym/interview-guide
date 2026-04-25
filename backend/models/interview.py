"""
====================================================
面试模型
====================================================
对应数据库中的 interviews 和 interview_messages 两张表。

interviews：面试会话（一次完整的模拟面试）
interview_messages：面试消息（面试中的每一句对话）

关系：一个面试会话包含多条消息（一对多）
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, TimestampMixin


class Interview(Base, TimestampMixin):
    """
    面试会话模型

    一次模拟面试的完整生命周期：
    1. 创建 → status="in_progress"，current_round=0
    2. 开始 → AI 发出开场白 + 第一题，current_round=1
    3. 多轮问答 → current_round 递增
    4. 结束 → status="completed"，生成 evaluation 和 report_url
    """
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # ---- 面试配置 ----
    skill_id: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # 技能方向标识，如 "java_backend"、"frontend"
    skill_name: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # 技能方向显示名，如 "Java 后端开发"
    difficulty: Mapped[str] = mapped_column(
        String(16), default="medium"
    )  # 难度：easy（初级）/ medium（中级）/ hard（高级）
    interview_type: Mapped[str] = mapped_column(
        String(16), default="text"
    )  # 面试类型：text（文字）/ voice（语音）

    # ---- 面试状态 ----
    status: Mapped[str] = mapped_column(
        String(32), default="in_progress"
    )  # 状态：in_progress / completed / cancelled
    current_round: Mapped[int] = mapped_column(
        Integer, default=0
    )  # 当前进行到第几轮（从 0 开始，0 表示还没开始）
    max_rounds: Mapped[int] = mapped_column(
        Integer, default=10
    )  # 最大轮数

    # ---- 评估结果（面试结束后填充）----
    total_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 总分（0-100）
    evaluation: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # 详细评估：维度得分、优势、不足、建议等
    report_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # PDF 评估报告路径

    # ---- 时间 ----
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(), server_default=func.now()
    )  # 开始时间
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(), nullable=True
    )  # 结束时间（面试结束前为空）

    # ---- 关系 ----
    user: Mapped["User"] = relationship(back_populates="interviews")
    messages: Mapped[list["InterviewMessage"]] = relationship(
        back_populates="interview",
        lazy="selectin",
        # 按 created_at 排序，确保消息按时间顺序返回
        order_by="InterviewMessage.created_at",
    )


class InterviewMessage(Base):
    """
    面试消息模型（不继承 TimestampMixin，只有 created_at）

    每一条消息代表面试中的一句话（面试官或候选人说的）
    """
    __tablename__ = "interview_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interviews.id", ondelete="CASCADE"),  # 面试删了消息也删
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # 角色："interviewer"（面试官）或 "candidate"（候选人）
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 消息文本内容
    message_type: Mapped[str] = mapped_column(
        String(16), default="text"
    )  # 消息类型："text"（文字）或 "audio"（语音，语音面试时用）
    round: Mapped[int] = mapped_column(
        Integer, default=1
    )  # 属于第几轮（一个 round 通常包含面试官的一题 + 候选人的回答）
    metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # 额外信息（如语音消息的时长、音频 URL 等）
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now()
    )  # 消息创建时间

    # ---- 关系 ----
    interview: Mapped["Interview"] = relationship(back_populates="messages")
