"""
====================================================
安全工具 —— JWT 令牌 + 密码哈希
====================================================

JWT（JSON Web Token）认证流程：
    1. 用户输入用户名密码 → 服务器验证 → 生成 JWT Token 返回
    2. 前端把 Token 存到 localStorage
    3. 之后每次请求都在 Header 带 Authorization: Bearer <token>
    4. 服务器解密 Token → 知道是哪个用户 → 处理请求

密码存储原则：
    绝对不能存明文密码！
    存储的是 bcrypt 哈希值（60 字符的随机字符串）。
    即使数据库泄露，攻击者也无法反推出原始密码。
    验证时：把用户输入的密码做同样的哈希 → 和数据库存的比较 → 一致就通过。
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt            # JWT 编解码库
from passlib.context import CryptContext   # 密码哈希库
from backend.config import get_settings

settings = get_settings()

# 密码哈希上下文
# schemes=["bcrypt"]：使用 bcrypt 算法（目前最安全的密码哈希算法之一）
# deprecated="auto"：自动标记过期的算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    密码 → 哈希值
    例："123456" → "$2b$12$eX8Vq...（60字符）"
    每次调用结果都不同（因为自动加盐），但都能验证同一个密码
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    从数据库取出哈希值，和用户输入的明文密码比较
    返回 True = 密码正确，False = 密码错误
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_jwt(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    创建 JWT Token

    参数：
        data: 要编码的数据，必须包含 "sub"（用户ID）
        expires_delta: 过期时间增量

    返回：JWT 字符串，例："eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.xxx"

    JWT 结构（三段，用 . 分隔）：
        第一段：Header（算法信息，Base64 编码）
        第二段：Payload（用户数据 + 过期时间，Base64 编码）
        第三段：Signature（用密钥对前两段签名，防止篡改）
    """
    to_encode = data.copy()
    # 设置过期时间和签发时间
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({
        "exp": expire,                       # 过期时间（必须，超出后 Token 失效）
        "iat": datetime.now(timezone.utc),    # 签发时间（可选，方便排查问题）
    })
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,              # 签名密钥（必须保密！）
        algorithm=settings.jwt_algorithm,      # 算法（HS256）
    )


def decode_jwt(token: str) -> dict | None:
    """
    解码 JWT Token
    成功返回 payload 字典（包含 sub、exp 等），失败返回 None
    失败原因：Token 过期、被篡改、密钥不对等
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
