"""
====================================================
知识库 API（含 SSE 流式 RAG 问答）
====================================================
接口列表：
    POST   /knowledgebases                    - 创建知识库
    GET    /knowledgebases                    - 知识库列表
    DELETE /knowledgebases/{id}               - 删除知识库
    POST   /knowledgebases/{id}/documents     - 上传文档
    GET    /knowledgebases/{id}/documents     - 文档列表
    GET    /knowledgebases/{id}/chat          - RAG 问答（SSE 流式）
"""

import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.user import User
from backend.models.knowledgebase import KnowledgeBase, KnowledgeDocument
from backend.schemas.common import ApiResponse, PageResult
from backend.schemas.knowledgebase import KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeDocumentOut
from backend.dependencies import get_current_user
from backend.services import knowledgebase_service
from backend.tasks.knowledgebase_tasks import process_document

router = APIRouter()


@router.post("")
async def create_kb(
    body: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建知识库"""
    kb = await knowledgebase_service.create_knowledge_base(
        db, user, body.name, body.description)
    return ApiResponse(data=KnowledgeBaseOut.model_validate(kb))


@router.get("")
async def list_kbs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """知识库列表（分页）"""
    kbs, total = await knowledgebase_service.get_user_knowledge_bases(
        db, user.id, page, page_size)
    return ApiResponse(data=PageResult(
        total=total, page=page, page_size=page_size,
        items=[KnowledgeBaseOut.model_validate(k) for k in kbs],
    ))


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除知识库（同时删除 ChromaDB 中的向量数据）"""
    result = await db.execute(select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="知识库不存在")
    knowledgebase_service.delete_kb_vectors(kb_id)
    await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    # 注意：这里简化了，实际应该用 delete 语句
    kb_to_delete = result.scalar_one()
    await db.delete(kb_to_delete)
    await db.flush()
    return ApiResponse(message="删除成功")


@router.post("/{kb_id}/documents")
async def upload_doc(
    kb_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    上传文档到知识库
    上传后触发 Celery 异步任务处理（解析→分块→向量化）
    """
    result = await db.execute(select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    file_data = await file.read()
    if len(file_data) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不能超过 50MB")

    doc = await knowledgebase_service.upload_document(
        db, kb, file_data,
        file.filename or "unknown",
        file.content_type or "application/octet-stream",
    )

    # 触发 Celery 异步任务
    task = process_document.delay(doc.id)
    doc.task_id = task.id
    await db.flush()

    return ApiResponse(data={
        "document_id": doc.id,
        "task_id": task.id,
        "status": "processing",
    })


@router.get("/{kb_id}/documents")
async def list_docs(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """知识库下的文档列表"""
    result = await db.execute(select(KnowledgeDocument).where(
        KnowledgeDocument.knowledge_base_id == kb_id
    ).order_by(KnowledgeDocument.created_at.desc()))
    docs = result.scalars().all()
    return ApiResponse(data=[KnowledgeDocumentOut.model_validate(d) for d in docs])


@router.get("/{kb_id}/chat")
async def rag_chat(
    kb_id: int,
    question: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    RAG 问答 —— SSE 流式响应

    SSE（Server-Sent Events）是什么？
        服务器向客户端持续推送数据的标准协议。
        格式：每条消息以 "data: " 开头，以 "\n\n" 结尾。
        例：data: {"type": "token", "content": "你"}\n\n

    前端怎么接收？
        用 fetch + ReadableStream 读取（因为 EventSource 不支持自定义 Header）

    为什么用流式？
        大模型生成回答可能需要几秒，如果等全部生成完才返回，
        用户要等很久。流式让用户看到文字一个个蹦出来（打字机效果）。
    """
    result = await db.execute(select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 调用 RAG 服务：检索相关文档 + 流式调用大模型
            token_stream, sources = await knowledgebase_service.rag_chat_stream(
                db, kb, question, top_k)

            # 第一步：发送引用的文档来源
            sources_data = json.dumps({
                "type": "sources",
                "sources": [
                    {"content": s["content"][:200], "score": s["score"], "source": s["source"]}
                    for s in sources
                ],
            }, ensure_ascii=False)
            yield f"data: {sources_data}\n\n"

            # 第二步：逐 token 发送（打字机效果）
            async for token in token_stream:
                if token:
                    token_data = json.dumps(
                        {"type": "token", "content": token}, ensure_ascii=False)
                    yield f"data: {token_data}\n\n"

            # 第三步：发送完成标记
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            # 出错时发送错误消息
            error_data = json.dumps(
                {"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    # 返回 StreamingResponse（FastAPI 会把它变成 SSE 响应）
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",       # 不缓存
            "Connection": "keep-alive",         # 保持连接
            "X-Accel-Buffering": "no",         # Nginx 不缓冲（否则流式效果失效）
        },
    )
