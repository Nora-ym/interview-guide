"""
文件存储服务
支持两种存储方式（通过 STORAGE_TYPE 环境变量切换）：

local：存到本地 ./uploads 文件夹（零依赖，推荐开发用）
minio：存到 MinIO 对象存储（生产环境推荐）
统一接口：
upload_file() → 上传
download_file() → 下载
delete_file() → 删除
get_presigned_url() → 获取临时下载链接
"""

import os
import uuid
from datetime import timedelta

from backend.config import get_settings

settings = get_settings()


def _ensure_dir(path: str):
    """确保目录存在，不存在就创建"""
    os.makedirs(path, exist_ok=True)


def upload_file(
    file_data: bytes,
    original_filename: str,
    folder: str = "uploads",
    content_type: str = "application/octet-stream",
) -> str:
    """
    上传文件

    参数：
        file_data: 文件的二进制数据
        original_filename: 原始文件名（如 "张三的简历.pdf"）
        folder: 存放文件夹
        content_type: MIME 类型

    返回：
        文件的存储路径，如 "resumes/a1b2c3d4.pdf"
    """
    # 生成唯一文件名：文件夹/随机UUID.扩展名
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
    object_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

    if settings.storage_type == "minio":
        import io
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )
    else:
        # 本地文件方式
        filepath = os.path.join(settings.upload_dir, object_name)
        _ensure_dir(os.path.dirname(filepath))
        with open(filepath, "wb") as f:
            f.write(file_data)

    return object_name


def download_file(object_name: str) -> bytes:
    """下载文件，返回二进制数据"""
    if settings.storage_type == "minio":
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        response = client.get_object(settings.minio_bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    else:
        filepath = os.path.join(settings.upload_dir, object_name)
        with open(filepath, "rb") as f:
            return f.read()


def delete_file(object_name: str):
    """删除文件"""
    if settings.storage_type == "minio":
        try:
            from minio import Minio
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            client.remove_object(settings.minio_bucket, object_name)
        except Exception:
            pass
    else:
        filepath = os.path.join(settings.upload_dir, object_name)
        if os.path.exists(filepath):
            os.remove(filepath)


def get_presigned_url(
    object_name: str,
    expires: timedelta = timedelta(hours=1),
) -> str:
    """
    获取临时下载链接

    MinIO：生成带签名的临时 URL（过期后无法访问）
    本地：返回后端代理下载的 API 地址
    """
    if settings.storage_type == "minio":
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        return client.presigned_get_object(
            settings.minio_bucket, object_name, expires=expires
        )
    else:
        return f"/api/v1/files/download/{object_name}"