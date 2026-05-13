"""
====================================================
全局配置文件
====================================================
这个文件负责从 .env 文件和环境变量中读取所有配置项。
整个项目所有需要配置的地方（数据库地址、API Key 等）都从这里获取。

使用方式：
    from backend.config import get_settings
    settings = get_settings()
    print(settings.mysql_host)  # 输出: localhost

为什么用 Pydantic Settings？
    1. 自动类型转换：环境变量是字符串，但我们需要 int/bool，Pydantic 自动转
    2. 自动校验：配置值不合法会报错
    3. 默认值：.env 中没配的项用代码里的默认值
    4. @lru_cache：全局单例，整个应用只创建一次 Settings 对象
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置类
    每个属性对应一个配置项：
    - 左边 = 属性名（代码中用 settings.xxx 访问）
    - 右边 = 默认值（.env 中没配就用这个）
    - 类型注解 = 自动把字符串转成对应类型
    """

    # 告诉 Pydantic 从哪里读取配置
    model_config = SettingsConfigDict(
        env_file=".env",           # 从 .env 文件读取
        env_file_encoding="utf-8",  # 文件编码
        case_sensitive=False,       # 环境变量名不区分大小写
    )

    # ================================================================
    # 应用基础配置
    # ================================================================
    app_name: str = "Interview Guide"  # 应用名称，显示在 API 文档标题
    app_env: str = "development"       # 运行环境：development / production
    app_debug: bool = True             # 调试模式（True 会打印 SQL 语句等）
    app_port: int = 8000               # 后端服务端口

    # ================================================================
    # MySQL 数据库配置
    # ================================================================
    mysql_host: str = "localhost"      # MySQL 地址
    mysql_port: int = 3306             # MySQL 端口
    mysql_user: str = "root"           # 用户名
    mysql_password: str = "123456"           # 密码（生产环境必须设！）
    mysql_database: str = "interview_guide"  # 数据库名

    @property
    def database_url(self) -> str:
        """
        异步数据库连接 URL
        格式：mysql+aiomysql://用户名:密码@主机:端口/数据库?参数
        aiomysql 是异步驱动，FastAPI 的 async 路由用它
        charset=utf8mb4 确保能存中文和 emoji
        """
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def database_url_sync(self) -> str:
        """
        同步数据库连接 URL
        格式：mysql+pymysql://用户名:密码@主机:端口/数据库?参数
        pymysql 是同步驱动，Celery Worker（同步环境）用它
        因为 Celery 不支持 async，所以需要单独一个同步 URL
        """
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    # ================================================================
    # Redis 配置
    # 用途：缓存、分布式锁、Celery 消息队列
    # ================================================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""    # 没有密码就留空字符串
    redis_db: int = 0           # Redis 有 16 个数据库（0-15），默认用 0

    @property
    def redis_url(self) -> str:
        """Redis 连接 URL，格式：redis://[:密码@]主机:端口/数据库编号"""
        pwd = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{pwd}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ================================================================
    # 文件存储配置
    # local = 存到本地 ./uploads 文件夹（零依赖，推荐开发用）
    # minio = 存到 MinIO 对象存储（生产环境推荐）
    # ================================================================
    storage_type: str = "local"       # 存储方式
    upload_dir: str = "./uploads"     # 本地存储目录

    # ================================================================
    # ChromaDB 向量数据库配置
    # ChromaDB 是纯 Python 的嵌入式向量数据库
    # 数据存在本地文件，不需要启动任何服务
    # 替代 PostgreSQL 的 pgvector 插件，用于知识库 RAG 的相似度搜索
    # ================================================================
    chroma_persist_dir: str = "./chroma_data"  # 向量数据持久化目录

    # ================================================================
    # AI / LLM 配置（阿里云百炼 DashScope 平台）
    # DashScope 提供兼容 OpenAI 格式的 API，所以可以用 LangChain 的 OpenAI 集成
    # 注册地址：https://bailian.console.aliyun.com/
    # ================================================================
    dashscope_api_key: str = ""                        # API Key（必须填！）
    dashscope_chat_model: str = "qwen-plus"            # 对话模型
    dashscope_embedding_model: str = "text-embedding-v3"  # 向量化模型
    dashscope_asr_model: str = "qwen3-speech"           # 语音识别模型
    dashscope_tts_model: str = "cosyvoice-v1-longxiaochun"  # 语音合成模型
    dashscope_tts_voice: str = "longxiaochun"           # TTS 语音角色

    # ================================================================
    # OpenAI 兼容接口（可选）
    # 如果不填 dashscope_api_key，会 fallback 到这里
    # ================================================================
    openai_api_base: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # ================================================================
    # JWT 认证配置
    # JWT（JSON Web Token）是一种无状态的认证方式：
    # 1. 用户登录 → 服务器生成一个加密 token 返回给前端
    # 2. 前端每次请求都在 Header 中带上这个 token
    # 3. 服务器解密 token 验证身份
    # 优点：不需要服务器存储 session，适合分布式部署
    # ================================================================
    jwt_secret_key: str = "change-me-in-production"  # 签名密钥（生产环境必须改！）
    jwt_algorithm: str = "HS256"                      # 加密算法
    jwt_expire_minutes: int = 1440                    # token 有效期（分钟），1440=24小时

    # ================================================================
    # CORS 跨域配置
    # CORS（Cross-Origin Resource Sharing）：
    # 浏览器的安全策略：默认不允许前端（localhost:5173）调用后端（localhost:8000）
    # 需要后端明确声明"我允许哪些前端地址访问我"
    # ================================================================
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的字符串转成列表：'a,b,c' → ['a', 'b', 'c']"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ================================================================
    # Celery 异步任务配置
    # ================================================================
    celery_broker_url: str = "redis://localhost:6379/1"     # 消息队列地址（用 Redis DB 1）
    celery_result_backend: str = "redis://localhost:6379/2"  # 结果存储地址（用 Redis DB 2）


# ================================================================
# 全局配置获取函数
# @lru_cache 装饰器的作用：把函数结果缓存起来，整个应用只创建一次 Settings 对象
# 这样不管调用多少次 get_settings()，返回的都是同一个对象（单例模式）
# ================================================================
@lru_cache()
def get_settings() -> Settings:
    return Settings()
