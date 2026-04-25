"""
====================================================
知识库模型
====================================================
对应数据库中的 3 张表：
1. knowledge_bases：知识库（用户创建的知识库容器）
2. knowledge_documents：知识库文档（上传到知识库的文件）
3. document_chunks：文档分块（文件被切成的小段，用于 RAG 检索）

什么是 RAG？
    RAG（Retrieval-Augmented Generation，检索增强生成）：
    1. 用户上传文档（如公司内部资料）
    2. 系统把文档切成小段，每段转成向量（一组数字）
    3. 用户提问时，先把问题也转成向量
    4. 在向量数据库中找与问题最相似的文档段落
    5. 把找到的段落 + 问题一起发给大模型，让大模型基于这些段落回答
    优点：大模型的回答不再是"瞎编"的，而是基于你提供的真实文档

为什么向量不存 MySQL？
    MySQL 不原生支持高效的向量相似度搜索。
    所以向量存在 ChromaDB（专门的向量数据库），MySQL 只存文本内容。
    通过 chunk_{数据库ID} 的方式关联。
"""

from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    """
    知识库模型

    知识库是一个"容器"，里面可以放多个文档。
    例如：用户创建了一个叫"公司内部技术文档"的知识库，
    然后往里面上传了 5 份 PDF 文件。
    """
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)  # 知识库名称
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 描述
    doc_count: Mapped[int] = mapped_column(Integer, default=0)  # 文档数量
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)  # 分块总数

    user: Mapped["User"] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        back_populates="knowledge_base", lazy="selectin"
    )


class KnowledgeDocument(Base, TimestampMixin):
    """
    知识库文档模型

    代表知识库中的一个文件。
    上传后会经过：解析 → 分块 → 向量化 的处理流程。
    """
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)  # 文档标题（文件名）
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)  # 文件存储路径
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 文件类型
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)  # 文件大小
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # 哈希（去重用）
    process_status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # 处理状态：pending / processing / completed / failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)  # 被切成了多少块
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 处理失败时的错误信息
    task_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # Celery 异步任务 ID

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", lazy="selectin"
    )


class DocumentChunk(Base):
    """
    文档分块模型

    一份文档被切成多个小块（chunk），每个 chunk 大约 500 个字符。
    切块太小 → 语义不完整；太大 → 检索不精准。500 是经验值。

    注意：向量不存这里！
    向量存在 ChromaDB 中，关联方式：
    ChromaDB 中的 id = "chunk_{MySQL 中这个 chunk 的 id}"
    例如：MySQL 中 id=42 的 chunk，在 ChromaDB 中的 id 是 "chunk_42"
    """
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 第几个块（从 0 开始，保持顺序）
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 分块的文本内容
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 大约多少个 token（粗略估算，1 个中文字 ≈ 1-2 个 token）
    # ⚠️ 向量存在 ChromaDB，不存 MySQL
    metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # 元数据：{"source": "文档名.pdf", "chunk_index": 0}
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
