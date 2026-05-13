"""
====================================================
简历异步任务
====================================================
这个文件定义了 Celery Worker 要执行的简历分析任务。

启动 Worker 的命令：
    celery -A backend.tasks.celery_app worker --loglevel=info

工作流程：
    1. 用户上传简历 → API 路由调用 analyze_resume.delay(resume_id)
    2. Celery 把任务消息存到 Redis
    3. Worker 从 Redis 取出任务，执行 analyze_resume() 函数
    4. 执行结果存回 Redis
    5. 前端通过 /resumes/{id}/status 接口查看进度

为什么用 delay()？
    .delay() 是 Celery 提供的快捷方法，等价于：
    analyze_resume.apply_async(args=[resume_id])
    它会把任务异步发送到消息队列，立即返回一个 AsyncResult 对象。
"""

import asyncio
from backend.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,                        # bind=True：self 参数指向任务实例（可以获取 task_id 等）
    autoretry_for=(Exception,),      # 遇到任何异常自动重试
    max_retries=3,                    # 最多重试 3 次
    retry_backoff=60,                 # 重试间隔：60秒 → 120秒 → 180秒（指数退避）
    retry_backoff_max=600,            # 最大间隔 10 分钟
    retry_jitter=True,                # 加随机抖动（避免多个任务同时重试造成"惊群效应"）
)
def analyze_resume(self, resume_id: int):
    """
    异步分析简历

    参数：
        self: Celery 任务实例（因为 bind=True）
            self.request.retries  → 当前是第几次重试
            self.request.id       → 任务 ID
        resume_id: 简历的数据库 ID

    为什么这里用同步函数而不是 async？
        Celery Worker 运行在同步环境中（不是 asyncio 事件循环）。
        但我们的 resume_service.analyze_resume() 是 async 函数。
        解决方案：创建一个新的事件循环来运行 async 函数。
    """
    from backend.services.resume_service import analyze_resume

    # 创建新的事件循环运行 async 函数
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(analyze_resume(resume_id))
    finally:
        loop.close()  # 用完必须关闭，否则会警告
