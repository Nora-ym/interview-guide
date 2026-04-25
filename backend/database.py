"""
====================================================
数据库连接管理
====================================================
这个文件负责创建和管理 SQLAlchemy 的数据库引擎和会话（Session）。

什么是 SQLAlchemy？
    Python 最强大的 ORM（对象关系映射）框架。
    ORM 的作用：用 Python 类代替 SQL 表，用 Python 对象代替表中的行。
    例如：User(username='张三') 代替  INSERT INTO users (username) VALUES ('张三')

什么是异步数据库？
    传统（同步）数据库操作：发送查询 → 等待 → 拿到结果 → 处理下一个请求
    期间线程被阻塞，不能处理其他请求。
    异步数据库操作：发送查询 → 去处理其他请求 → 结果回来了再回来处理
    FastAPI 是异步框架，配合异步数据库才能发挥最大性能。

Session 是什么？
    Session 是与数据库的一次"对话"。
    你通过 Session 来增删改查数据，最后 commit 提交（就像 git commit）。
    每个 HTTP 请求应该有自己独立的 Session，互不干扰。
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,           # 异步会话类
    async_sessionmaker,     # 异步会话工厂（用来创建 Session）
    create_async_engine,    # 创建异步引擎
)

from backend.config import get_settings

# 获取全局配置
settings = get_settings()

# ================================================================
# 创建数据库引擎
# Engine 是连接池的管理器，它负责：
# 1. 维护一组数据库连接（连接池）
# 2. 把 SQL 语句发给数据库执行
# 3. 管理连接的生命周期（创建、回收）
#
# 参数说明：
# - echo=True：打印每条 SQL 语句（调试用，生产环境关掉）
# - pool_size=20：连接池保持 20 个连接
# - max_overflow=10：突发时最多额外创建 10 个连接
# - pool_pre_ping=True：每次从池中取出连接时先 ping 一下，确认连接没断
# - pool_recycle=3600：连接超过 1 小时自动回收重建（防止 MySQL 的 wait_timeout 断连）
# ================================================================
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ================================================================
# 创建会话工厂
# async_sessionmaker 用来创建 AsyncSession 实例
# 就像一个"Session 生产车间"，需要 Session 时找它要就行
#
# 参数说明：
# - expire_on_commit=False：commit 之后不立即过期对象
#   （默认 True 会在 commit 后清空对象的属性，导致取值报错，关掉更方便）
# - autocommit=False：不自动提交（需要手动 session.commit()）
# - autoflush=False：不自动 flush（需要手动 session.flush()）
# ================================================================
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入函数：获取数据库 Session

    依赖注入是什么？
        FastAPI 的一个强大功能。你不需要在每个路由函数里手动创建和关闭 Session。
        只要在参数里写 db: AsyncSession = Depends(get_db)，FastAPI 就会：
        1. 请求进来时 → 自动调用 get_db() 创建 Session
        2. 路由函数执行完 → 自动 commit
        3. 如果出错了 → 自动 rollback
        4. 无论如何 → 自动关闭 Session

    使用示例：
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
            # 这里不需要手动 db.close()，FastAPI 会自动处理
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session        # 把 session 交给路由函数使用
            await session.commit()  # 路由函数正常执行完 → 提交事务
        except Exception:
            await session.rollback()  # 出错了 → 回滚事务（撤销所有修改）
            raise                     # 把异常继续抛出，让 FastAPI 返回 500 错误
        finally:
            await session.close()     # 无论如何 → 关闭 Session（归还连接池）
