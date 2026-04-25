"""
Redis 缓存服务
封装 Redis 的常用操作，提供简洁的接口。

Redis 是什么？
内存数据库，读写极快（每秒 10 万次操作）。
常见用途：
1. 缓存热点数据（减少数据库查询）
2. 分布式锁（防止并发冲突）
3. 消息队列（Celery 用它传递任务）

本项目中 Redis 的用途：
1. 面试题目去重：用 Redis Set 记录已问过的题目
2. 面试会话上下文：缓存面试状态
3. Celery 消息队列：传递异步任务
"""

import json
from typing import Any, Optional

# Redis 的异步 Python 客户端
import redis.asyncio as aioredis

from backend.config import get_settings

settings = get_settings()

# 全局 Redis 客户端（单例）
_redis_pool: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """
    初始化 Redis 连接
    在应用启动时调用（main.py 的 lifespan 中）
    """
    global _redis_pool
    _redis_pool = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,  # 自动把 bytes 解码成 str
        max_connections=20,
    )
    return _redis_pool


async def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端（如果没初始化就先初始化）"""
    global _redis_pool
    if _redis_pool is None:
        return await init_redis()
    return _redis_pool


async def close_redis():
    """关闭 Redis 连接（应用关闭时调用）"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def cache_get(key: str) -> Optional[Any]:
    """
    从缓存中获取值

    参数：
        key: 缓存键，如 "user:123"
    返回：
        缓存的值（自动从 JSON 反序列化），不存在返回 None
    """
    r = await get_redis()
    val = await r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


async def cache_set(key: str, value: Any, ttl: int = 3600):
    """
    设置缓存

    参数：
        key: 缓存键
        value: 要缓存的值（dict/list 自动序列化为 JSON）
        ttl: 过期时间（秒），默认 3600 = 1 小时
    """
    r = await get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    await r.setex(key, ttl, value)


async def add_asked_question(interview_id: int, question_hash: str):
    """
    记录已问过的面试题目

    用 Redis Set 数据结构：Set 中的元素自动去重
    同一个 interview_id 下，相同的 question_hash 只会存一份

    参数：
        interview_id: 面试 ID
        question_hash: 题目的哈希值（用题目内容算 SHA256）
    """
    r = await get_redis()
    key = f"interview:asked:{interview_id}"
    await r.sadd(key, question_hash)
    await r.expire(key, 7200)  # 2 小时后自动删除


async def is_question_asked(interview_id: int, question_hash: str) -> bool:
    """
    检查某个题目是否已经问过

    返回：True = 已问过，False = 没问过
    """
    r = await get_redis()
    key = f"interview:asked:{interview_id}"
    return bool(await r.sismember(key, question_hash))


async def cache_interview_context(interview_id: int, context: dict, ttl: int = 7200):
    """缓存面试会话上下文"""
    await cache_set(f"interview:context:{interview_id}", context, ttl)


async def get_interview_context(interview_id: int) -> Optional[dict]:
    """获取面试会话上下文"""
    return await cache_get(f"interview:context:{interview_id}")