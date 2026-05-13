"""
====================================================
简历模型
====================================================
对应数据库中的 resumes 表。
每个用户可以上传多份简历，每份简历会经过 AI 分析。
关于简历的信息会保存到这里
"""
from sqlalchemy import String, BigInteger, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON  # MySQL 8.0 原生支持 JSON 类型
from backend.models.base import Base, TimestampMixin

class Resume(Base, TimestampMixin):
    """
    简历模型

    一份简历的生命周期：
    1. 用户上传文件 → file_url、file_type、file_size 被填充
    2. 异步解析 → parsed_text 被填充（从文件中提取的文字）
    3. 异步 AI 分析 → analysis_status 变为 "completed"，analysis_result 被填充
    4. 生成 PDF 报告 → report_url 被填充
    """
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),  # 外键，CASCADE = 用户删了简历也删
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)  # 简历标题（通常是文件名）

    # ---- 文件信息 ----
    file_url: Mapped[str] = mapped_column(
        String(512), nullable=False
    )  # 文件在存储系统中的路径，如 "resumes/abc123.pdf"
    file_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 文件扩展名：pdf、docx、txt 等
    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # 文件大小（字节），用 BigInteger 因为大文件可能超过 2GB（int 上限）

    # ---- 内容信息 ----
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # 文件内容的 SHA256 哈希值，用于去重（相同内容不重复上传）
    parsed_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 从文件中解析出的纯文本内容（供 AI 分析用）

    # ---- 分析信息 ----
    analysis_status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # 分析状态：pending / analyzing / completed / failed
    analysis_result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # AI 分析结果，JSON 格式，如：{"overall_score": 85, "strengths": [...], ...}
    report_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # 生成的 PDF 分析报告的文件路径
    task_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # Celery 异步任务 ID（前端可以通过这个 ID 查询任务进度）

    # ---- 关系 ----
    user: Mapped["User"] = relationship(back_populates="resumes")
