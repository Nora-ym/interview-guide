"""
====================================================
模型基类 基类和时间戳
====================================================
所有数据库模型的公共基类。

什么是 ORM 模型？
    一个 Python 类 = 数据库中的一张表
    类的属性 = 表的列
    类的实例 = 表的一行数据

例如：
    class User(Base):
        id = mapped_column(Integer, primary_key=True)
        username = mapped_column(String(64))

    等价于 SQL：
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username VARCHAR(64)
    );

Mapped[T] 是什么？
    SQLAlchemy 2.0 的新语法，声明"这个属性映射到数据库的某列"
    Mapped[int] 表示这个属性是 int 类型
    Mapped[str | None] 表示这个属性是 str 或 None（允许为空）
"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """
    所有模型的抽象基类
    继承 DeclarativeBase 后，SQLAlchemy 才知道这个类是 ORM 模型
    所有模型都要直接或间接继承 Base
    """
    pass

class TimestampMixin:
    """
    时间戳混入类

    "混入"（Mixin）是一种代码复用技巧：
    多个表都有 created_at 和 updated_at 字段，
    与其每个表都写一遍，不如抽到一个 Mixin 里，然后继承它。

    使用方法：
        class User(Base, TimestampMixin):  # 继承了 created_at 和 updated_at
            ...
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),                    # MySQL 的 DATETIME 类型
        server_default=func.now(),     # 默认值 = 当前时间（由数据库生成，不是 Python）
        nullable=False,                # 不允许为空
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),     # 创建时默认当前时间
        onupdate=func.now(),           # 每次更新记录时自动刷新为当前时间
        nullable=False,
    )
