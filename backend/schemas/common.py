"""
====================================================
通用 Schema
====================================================
Schema（Pydantic 模型）定义了 API 请求和响应的数据结构。
与 ORM Model 的区别：
    - ORM Model（models/）：对应数据库表，定义怎么存
    - Schema（schemas/）：对应 API 接口，定义怎么传/返回

例如：
    models.User  →  数据库 users 表的 Python 表示
    schemas.UserOut  →  返回给前端的用户信息 JSON 格式

Pydantic 的好处：
    1. 自动校验：字符串太长、类型不对、必填为空 → 自动报错
    2. 自动序列化：Python 对象 → JSON 字符串
    3. 自动生成 OpenAPI 文档：FastAPI 读取 Schema 自动生成 Swagger 文档
"""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")  # 泛型类型变量，让 ApiResponse 可以包装任何类型


class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 响应格式
    所有接口都返回这个格式：
    {
        "code": 200,
        "message": "success",
        "data": { ... }  // 具体数据，可能是任何类型
    }

    使用示例：
        return ApiResponse(data=user)              # 成功，带数据
        return ApiResponse(message="删除成功")       # 成功，无数据
        return ApiResponse(code=400, message="参数错误")  # 失败
    """
    code: int = 200  # 状态码，200=成功
    message: str = "success"  # 提示信息
    data: T | None = None  # 具体数据（泛型，可以是任意类型）


class PageResult(BaseModel, Generic[T]):
    """
    分页结果格式

    返回格式：
    {
        "total": 100,     // 总记录数
        "page": 1,        // 当前页码
        "page_size": 20,  // 每页数量
        "items": [...]    // 当前页的数据列表
    }
    """
    total: int  # 总记录数
    page: int  # 当前页码
    page_size: int  # 每页数量
    items: list[T]  # 当前页的数据列表
