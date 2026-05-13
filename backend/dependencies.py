"""
====================================================
公共依赖注入
====================================================
这个文件定义了在多个路由中复用的"依赖项"。
最典型的是"获取当前登录用户"——几乎每个需要登录的接口都要用。

依赖注入的原理：
    FastAPI 看到 Depends(get_current_user) 时，会先执行 get_current_user()，
    把返回值赋给参数。如果函数抛出异常（比如 token 无效），直接返回错误响应。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db          # 数据库 Session 依赖
from backend.models.user import User          # 用户模型
from backend.utils.security import decode_jwt  # JWT 解码函数

# HTTPBearer：告诉 FastAPI 从请求头 Authorization: Bearer xxx 中提取 token
security_scheme = HTTPBearer()


async def get_current_user(
    # FastAPI 自动从请求头提取 Bearer token
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    # 自动获取数据库 Session
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前登录用户（必须登录才能调用）

    工作流程：
    1. 从请求头取出 JWT token
    2. 解码 token，拿到用户 ID
    3. 从数据库查询该用户
    4. 检查用户是否存在、是否被禁用
    5. 返回 User 对象

    如果任何一步失败，抛出 HTTPException（FastAPI 自动返回 401 错误）

    使用示例：
        @router.get("/my-profile")
        async def my_profile(user: User = Depends(get_current_user)):
            return {"username": user.username}
    """
    # 第一步：提取 token 字符串
    token = credentials.credentials

    # 第二步：解码 token，得到 {"sub": "123", "username": "zhangsan", "exp": 1700000000}
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )

    # 第三步：从 payload 中取用户 ID（sub 是 JWT 标准中的"主题"字段，我们存的是用户 ID）
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户信息",
        )

    # 第四步：从数据库查用户
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()  # 找到返回 User 对象，没找到返回 None

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 第五步：检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user  # 一切正常，返回 User 对象


async def get_optional_user(
    # auto_error=False：没有 token 时不报错，返回 None
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    可选认证：有 token 就返回用户，没有就返回 None
    用于"登录和未登录都能访问"的接口
    """
    if credentials is None:
        return None  # 没有 token，返回 None（不报错）
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None  # token 无效，返回 None（不报错）
