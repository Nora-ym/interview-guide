"""
知识库服务（RAG 问答核心）
RAG（Retrieval-Augmented Generation）完整流程：

上传文档 → 解析文本 → 切分成小块 → 每块转成向量 → 存入 ChromaDB
↓
用户提问 → 问题转成向量 → 在 ChromaDB 中找最相似的块 → 组装成 Prompt → 大模型生成回答

ChromaDB 和 MySQL 的关系：
MySQL 存：文档元数据、分块文本内容（人类可读）
ChromaDB 存：分块的向量（机器可比较）
通过 "chunk_{MySQL中分块的ID}" 关联两者
"""

import io
import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledgebase import KnowledgeBase, KnowledgeDocument, DocumentChunk
from backend.models.user import User
from backend.services.ai_service import chat_stream, embed_texts, embed_query
from backend.services.storage_service import upload_file, download_file
from backend.utils.document_parser import DocumentParser
from backend.config import get_settings

settings = get_settings()


def get_chroma_collection(kb_id: int) -> chromadb.Collection:
    """
    获取知识库对应的 ChromaDB 集合

    ChromaDB 中"集合"类似数据库中的"表"：
    - 每个 MySQL 知识库对应一个 ChromaDB Collection
    - Collection 名为 "kb_{知识库ID}"
    """
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=f"kb_{kb_id}",
        metadata={"hnsw:space": "cosine"},
    )


async def create_knowledge_base(
    db: AsyncSession, user: User, name: str, description: str | None = None,
) -> KnowledgeBase:
    """创建知识库"""
    kb = KnowledgeBase(user_id=user.id, name=name, description=description)
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return kb


async def get_user_knowledge_bases(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 20,
) -> tuple[list[KnowledgeBase], int]:
    """获取用户的 知识库列表（分页）"""
    query = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
    count_q = select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(
        query.order_by(KnowledgeBase.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total or 0


async def upload_document(
    db: AsyncSession, kb: KnowledgeBase,
    file_data: bytes, filename: str, content_type: str,
) -> KnowledgeDocument:
    """上传文档到知识库（只存储文件，后续由 Celery 异步处理）"""
    file_url = upload_file(file_data, filename, folder="knowledge", content_type=content_type)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_hash = DocumentParser.compute_hash(io.BytesIO(file_data))
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        title=filename.rsplit(".", 1)[0] if "." in filename else filename,
        file_url=file_url, file_type=ext, file_size=len(file_data),
        content_hash=content_hash, process_status="pending",
    )
    db.add(doc)
    await db.flush()
    return doc


def _split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    """
    把长文本切成小块

    chunk_overlap：块与块之间有重叠，避免在句子中间切断
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [{"content": c, "token_count": len(c)} for c in chunks]


async def process_document(document_id: int) -> dict:
    """
    异步处理文档（给 Celery Worker 调用）

    完整流程：
    1. 下载文件 → 2. 解析文本 → 3. 分块
    4. 保存到 MySQL → 5. 向量化存入 ChromaDB
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.config import get_settings

    engine = create_engine(get_settings().database_url_sync)
    with Session(engine) as db:
        doc = db.get(KnowledgeDocument, document_id)
        if not doc:
            raise ValueError(f"文档不存在: {document_id}")
        doc.process_status = "processing"
        db.commit()

        try:
            file_data = download_file(doc.file_url)
            parsed_text = DocumentParser.parse(io.BytesIO(file_data), f"{doc.title}.{doc.file_type}")
            chunks = _split_text(parsed_text)
            doc.chunk_count = len(chunks)

            # 保存到 MySQL
            db_chunks = []
            for i, chunk in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=doc.id, knowledge_base_id=doc.knowledge_base_id,
                    chunk_index=i, content=chunk["content"],
                    token_count=chunk.get("token_count"),
                    metadata={"source": doc.title, "chunk_index": i},
                )
                db.add(db_chunk)
                db.flush()
                db_chunks.append(db_chunk)
            db.commit()

            # 向量化并存入 ChromaDB
            embeddings = await embed_texts([c["content"] for c in chunks])
            collection = get_chroma_collection(doc.knowledge_base_id)
            collection.upsert(
                ids=[f"chunk_{c.id}" for c in db_chunks],
                documents=[c["content"] for c in chunks],
                embeddings=embeddings,
                metadatas=[{
                    "db_chunk_id": c.id, "document_id": doc.id,
                    "source": doc.title, "chunk_index": i,
                } for i, c in enumerate(db_chunks)],
            )

            kb = db.get(KnowledgeBase, doc.knowledge_base_id)
            if kb:
                kb.chunk_count += len(chunks)
            db.commit()
            return {"status": "completed", "chunks": len(chunks)}

        except Exception as e:
            doc.process_status = "failed"
            doc.error_message = str(e)
            db.commit()
            raise


async def rag_search(
    db: AsyncSession, kb_id: int, query_text: str, top_k: int = 5,
) -> list[dict]:
    """
    向量相似度搜索（RAG 的 "R" 部分）

    流程：把问题转成向量 → 在 ChromaDB 中找最相似的 top_k 个文本块
    """
    query_embedding = await embed_query(query_text)
    collection = get_chroma_collection(kb_id)
    results = collection.query(
        query_embeddings=[query_embedding], n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    documents = []
    if results and results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            similarity = max(0, 1 - distance)
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            documents.append({
                "content": results["documents"][0][i],
                "score": round(similarity, 4),
                "source": meta.get("source", ""),
                "chunk_id": meta.get("db_chunk_id"),
            })
    return documents


async def rag_chat_stream(
    db: AsyncSession, kb: KnowledgeBase, question: str, top_k: int = 5,
) -> tuple:
    """
    RAG 问答（流式）（RAG 的 "G" 部分）

    流程：检索相关文档 → 拼成上下文 → 流式调用大模型
    返回：(token_stream, sources)
    """
    documents = await rag_search(db, kb.id, question, top_k)
    context = "\n\n".join([f"[{d['source']}]: {d['content']}" for d in documents])
    system_prompt = (
        f"你是知识库问答助手，基于参考内容回答，不编造信息。\n\n参考内容：\n{context}"
    )
    return (
        chat_stream([{"role": "user", "content": question}],
                    system_prompt=system_prompt, temperature=0.3),
        documents,
    )


def delete_kb_vectors(kb_id: int):
    """删除知识库的所有向量（ChromaDB 中的数据）"""
    try:
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        client.delete_collection(f"kb_{kb_id}")
    except Exception:
        pass