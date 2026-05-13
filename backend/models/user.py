"""
====================================================
用户模型
====================================================
对应数据库中的 users 表。
存储用户的基本信息：用户名、邮箱、密码（加密后）、头像等。
"""

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    """
    用户模型
    映射到数据库：
    CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) UNIQUE NOT NULL,
        email VARCHAR(256) UNIQUE NOT NULL,
        hashed_password VARCHAR(256) NOT NULL,
        avatar_url VARCHAR(512),
        is_active BOOLEAN DEFAULT TRUE,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT NOW(),
        updated_at DATETIME DEFAULT NOW()
    );
    """
    __tablename__ = "users"  # 指定表名

    # ---- 字段定义 ----
    id: Mapped[int] = mapped_column(
        primary_key=True,   # 主键
        autoincrement=True,  # 自增
    )
    username: Mapped[str] = mapped_column(
        String(64),      # VARCHAR(64)
        unique=True,       # 唯一约束（不能有两个相同用户名）
        index=True,        # 建索引（按用户名查询更快）
        nullable=False,    # 不允许为空
    )
    email: Mapped[str] = mapped_column(
        String(256),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,     # 允许为空（用户可以不设置头像）
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,      # 默认激活
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,     # 默认不是管理员
    )

    # ---- 关系定义（relationship）----
    # relationship 声明"这个用户有哪些关联数据"
    # 不在数据库中创建列，只是告诉 ORM 如何关联查询
    # lazy="selectin" 表示访问这个属性时，自动用 JOIN 一次性查出关联数据（避免 N+1 查询问题）
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user",    # 对方模型的哪个属性指向我
        lazy="selectin",           # 加载策略
    )
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    schedules: Mapped[list["InterviewSchedule"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
