"""
====================================================
模型包初始化 —— 导入所有模型
====================================================
这里集中导入所有模型类，确保 Alembic 迁移时能发现所有表。
如果新增了模型但忘了在这里导入，Alembic 的 autogenerate 会检测不到新表！
"""
from backend.models.base import Base, TimestampMixin
from backend.models.user import User
from backend.models.resume import Resume
from backend.models.interview import Interview, InterviewMessage
from backend.models.knowledgebase import (
    KnowledgeBase,
    KnowledgeDocument,
    DocumentChunk,
)
from backend.models.schedule import InterviewSchedule
