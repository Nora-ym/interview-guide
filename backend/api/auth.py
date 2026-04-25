"""
====================================================
认证 API
====================================================
处理用户注册、登录、获取当前用户信息。

JWT 认证流程：
    注册：用户名+邮箱+密码 → 创建用户 → 返回 Token
    登录：用户名+密码 → 验证 → 返回 Token
    之后：每次请求带 Token → 后端自动识别用户
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import UserRegister, UserLogin, TokenResponse, UserOut
from backend.utils.security import hash_password, verify_password, create_jwt
from backend.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(
    body: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    注册新用户
    请求体：{"username": "zhangsan", "email": "zhangsan@example.com", "password": "123456"}
    返回：{"access_token": "xxx", "user": {...}}
    """
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否已存在
    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 创建用户（密码要哈希后存储，绝不存明文！）
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()       # 写入数据库拿到 ID
    await db.refresh(user)  # 刷新对象

    # 生成 JWT Token
    token = create_jwt({"sub": str(user.id), "username": user.username})

    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录
    请求体：{"username": "zhangsan", "password": "123456"}
    返回：{"access_token": "xxx", "user": {...}}
    """
    # 查找用户
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    # 验证用户名和密码
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 检查账号状态
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    # 生成 Token
    token = create_jwt({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    请求头：Authorization: Bearer <token>
    返回：用户信息（不需要传任何参数，Token 里就有用户 ID）
    """
    return UserOut.model_validate(user)
