"""简历相关 Schema"""
from datetime import datetime
from pydantic import BaseModel


class ResumeOut(BaseModel):
    """简历输出 Schema（返回给前端的数据格式）"""
    id: int
    title: str
    file_url: str
    file_type: str
    file_size: int
    analysis_status: str       # pending/analyzing/completed/failed
    analysis_result: dict | None = None  # AI 分析结果（JSON 对象）
    report_url: str | None = None          # PDF 报告下载链接
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
