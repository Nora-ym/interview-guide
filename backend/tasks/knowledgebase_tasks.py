"""
====================================================
知识库异步任务 + 定时任务
====================================================
两个任务：
1. process_document - 处理上传的文档（解析→分块→向量化）
2. expire_schedules - 定时过期面试安排（由 Celery Beat 调用）
"""

import asyncio
from backend.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=60,
)
def process_document(self, document_id: int):
    """
    异步处理文档
    流程：下载文件 → 解析文本 → 切分块 → 保存 MySQL → 向量化存 ChromaDB
    """
    from backend.services.knowledgebase_service import process_document

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(process_document(document_id))
    finally:
        loop.close()


@celery_app.task
def expire_schedules():
    """
    定时任务：自动过期面试安排
    每小时执行一次，把 interview_time 已过且状态为 upcoming 的记录改为 completed

    这个任务在 celery_app.py 的 beat_schedule 中配置：
        "expire-schedules": {"schedule": 3600.0, ...}

    启动 Beat 调度器的命令：
        celery -A backend.tasks.celery_app beat --loglevel=info
    """
    from backend.services.schedule_service import auto_expire_schedules

    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(auto_expire_schedules())
        return {"expired_count": count}
    finally:
        loop.close()
