"""
====================================================
Celery 应用配置
====================================================
Celery 是 Python 的分布式任务队列框架。

什么是任务队列？
    把耗时的操作扔到后台执行，不阻塞用户请求。
    比如：上传简历后，AI 分析需要 30 秒。
    如果同步执行，用户要等 30 秒才能看到页面。
    用 Celery：上传后 0.1 秒返回 → 后台慢慢分析 → 前端轮询进度。

架构图：
    FastAPI ──发送任务──→ Redis ──取任务──→ Celery Worker ──执行──→ 存结果到 Redis
                                                                    ↑
    Celery Beat ──定时发任务──→ Redis ──────────────────────────────┘

beat_schedule 配置定时任务：
    "expire-schedules": 每小时执行一次，把过期的面试安排标记为 completed
"""

from celery import Celery
from backend.config import get_settings

settings = get_settings()

# 创建 Celery 实例
# 参数说明：
#   "interview_guide" - 应用名（显示在日志和监控中）
#   broker - 消息队列地址（任务从这里取）
#   backend - 结果存储地址（任务执行结果存到这里）
celery_app = Celery(
    "interview_guide",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery 全局配置
celery_app.conf.update(
    task_serializer="json",         # 任务序列化格式（JSON 通用、可读）
    accept_content=["json"],        # 只接受 JSON 格式的任务消息
    result_serializer="json",       # 结果也用 JSON 序列化
    timezone="Asia/Shanghai",        # 时区（定时任务用到）
    enable_utc=True,                 # 内部用 UTC 存储（避免夏令时问题）
    task_track_started=True,         # 跟踪任务开始时间（可以区分"排队中"和"执行中"）
    task_acks_late=True,             # 任务执行完才确认（防止 Worker 中途崩溃丢任务）
    worker_prefetch_multiplier=1,    # 每次只预取 1 个任务（避免某个 Worker 堆积太多长任务）
    task_default_rate_limit="10/m",  # 默认速率限制：每分钟最多 10 个任务（防止大模型 API 被限流）

    # 定时任务配置（由 Celery Beat 调度器执行）
    beat_schedule={
        "expire-schedules": {
            "task": "backend.tasks.knowledgebase_tasks.expire_schedules",
            "schedule": 3600.0,       # 每 3600 秒 = 1 小时执行一次
            "args": (),               # 不传参数
        }
    },
)

# 自动发现 tasks 包下的所有任务模块
# 这样不用手动 import 每个任务文件
celery_app.autodiscover_tasks(["backend.tasks"])
