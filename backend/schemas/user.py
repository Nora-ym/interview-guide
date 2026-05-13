"""
====================================================
用户相关 Schema
====================================================
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    """
    注册请求 Schema
    定义了用户注册时需要传什么数据
    """
    username: str = Field(
        min_length=3, max_length=64,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="用户名：3-64 位字母、数字、下划线"
    )
    email: EmailStr = Field(description="邮箱地址，Pydantic 自动校验格式")
    password: str = Field(
        min_length=6, max_length=128,
        description="密码：至少 6 位"
    )


class UserLogin(BaseModel):
    """登录请求 Schema"""
    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class TokenResponse(BaseModel):
    """登录成功后的响应"""
    access_token: str = Field(description="JWT Token，前端存到 localStorage")
    token_type: str = "bearer"  # 固定值，HTTP Authorization Header 的标准格式
    user: "UserOut"  # 用户信息


class UserOut(BaseModel):
    """
    用户信息输出 Schema
    定义了返回给前端的用户信息包含哪些字段

    model_config = {"from_attributes": True} 的含义：
    允许从 ORM 对象直接创建（UserOut.model_validate(user_obj)）
    Pydantic 会自动把 ORM 对象的属性映射到 Schema 的字段
    """
    id: int
    username: str
    email: str
    avatar_url: str | None = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
