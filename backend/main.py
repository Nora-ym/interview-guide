"""
====================================================
FastAPI 应用主入口
====================================================
整个后端的启动文件。

启动命令：
    uvicorn backend.main:app --reload

启动后可以访问：
    http://localhost:8000/docs  → 自动生成的 Swagger API 文档
    http://localhost:8000/      → 根路径
    http://localhost:8000/health → 健康检查

lifespan 是什么？
    FastAPI 的生命周期管理器。
    应用启动时执行 yield 之前的代码（初始化连接等）
    应用关闭时执行 yield 之后的代码（清理资源等）
    替代了旧版的 @app.on_event("startup") / @app.on_event("shutdown")
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from backend.config import get_settings
from backend.api.router import api_router
from backend.services.cache_service import init_redis, close_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动阶段（yield 之前）：
    1. 连接 Redis（失败了只警告，不影响核心功能）
    2. 加载技能方向定义
    3. 打印启动日志

    运行阶段（yield）：
    应用正常运行，处理请求

    关闭阶段（yield 之后）：
    关闭 Redis 连接
    """
    logger.info(f"🚀 {settings.app_name} 启动中...")

    # 尝试连接 Redis（不是必须的，失败了只警告）
    try:
        await init_redis()
        logger.info("✅ Redis 连接成功")
    except Exception as e:
        logger.warning(f"⚠️ Redis 连接失败（不影响核心功能）: {e}")

    # 加载技能方向
    from backend.services.interview_service import load_skills
    load_skills()
    logger.info("✅ 技能方向加载完成")

    logger.info(f"🚀 {settings.app_name} 启动完成!")
    yield  # 应用在这里运行

    # 关闭资源
    await close_redis()


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,  # 绑定生命周期
    docs_url="/docs",   # Swagger 文档地址
)

# 添加 CORS 中间件
# 作用：允许前端（localhost:5173）跨域访问后端（localhost:8000）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # 允许的前端地址列表
    allow_credentials=True,   # 允许携带 Cookie
    allow_methods=["*"],       # 允许所有 HTTP 方法
    allow_headers=["*"],       # 允许所有请求头
)

# 注册所有 API 路由（前缀 /api/v1）
app.include_router(api_router)


# ---- 健康检查接口（不需要认证）----
@app.get("/health")
async def health():
    """健康检查（用于 Docker healthcheck 和负载均衡器探活）"""
    return {"status": "ok", "app": settings.app_name}


@app.get("/")
async def root():
    """根路径"""
    return {"app": settings.app_name, "docs": "/docs"}
