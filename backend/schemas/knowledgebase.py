"""知识库相关 Schema"""
from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(min_length=1, max_length=256, description="知识库名称")
    description: str | None = Field(default=None, description="描述")


class KnowledgeBaseOut(BaseModel):
    """知识库输出"""
    id: int
    name: str
    description: str | None = None
    doc_count: int
    chunk_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class KnowledgeDocumentOut(BaseModel):
    """知识库文档输出"""
    id: int
    title: str
    file_type: str
    file_size: int
    process_status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
