from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from search_similar_documents import DocumentSearcher
from add_document_from_file import add_document_from_file
from rag_chat import RAGChatService
import chat_model
import reranker
import command_router
import paper_search_service
import json
import logging
import queue
import sqlite3
import threading
import time
import numpy as np
from typing import List, Dict, Any
from embedding import get_embedding, get_embeddings
import faiss
import os
from datetime import datetime

app = FastAPI(title="RAG系统API", description="支持文档管理、检索和对话功能")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("paper_search.api")

# CORS 配置：允许前端跨域访问云端 API
raw_allow_origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://39.107.73.88:5173,https://39.107.73.88",
)
allow_origins = [origin.strip() for origin in raw_allow_origins.split(",") if origin.strip()]
if not allow_origins:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

searcher = DocumentSearcher()
DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-r1:1.5b").strip() or "deepseek-r1:1.5b"

# 创建RAG服务实例 - 复用searcher避免重复初始化
rag_service = RAGChatService(searcher=searcher, model_type=DEFAULT_CHAT_MODEL)


def _paper_search_enabled() -> bool:
    return os.getenv("PAPER_SEARCH_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _paper_summary_prompt(
    plan: Dict[str, Any],
    papers: List[Dict[str, Any]],
    local_documents: List[Dict[str, Any]] = None,
    user_topic: str = "",
) -> str:
    queries = plan.get("queries", [])
    return (
        "用户触发了 /论文检索。请结合本地知识库检索结果和 arXiv 论文检索结果，用中文给出研究型总结。\n"
        "要求：\n"
        "1. 先说明根据上下文生成的 arXiv 检索方向。\n"
        "2. 同时利用本地知识库内容和论文摘要，回答用户当前主题。\n"
        "3. 总结代表性论文分别解决的问题，以及它们与本地资料的关系。\n"
        "4. 不要编造论文信息，只使用提供的论文标题、摘要、作者、日期和链接。\n\n"
        f"用户主题：{user_topic or '根据最近对话判断'}\n"
        f"检索 query：{json.dumps(queries, ensure_ascii=False)}\n"
        f"本地知识库片段数量：{len(local_documents or [])}\n"
        f"论文数量：{len(papers)}"
    )


def _paper_search_progress_interval() -> float:
    return float(os.getenv("PAPER_SEARCH_PROGRESS_INTERVAL", "5"))


def _paper_search_total_timeout() -> float:
    return float(os.getenv("PAPER_SEARCH_TOTAL_TIMEOUT", "90"))


def _augment_history_for_paper_search(history: List[Dict[str, str]] = None, current_message: str = "") -> List[Dict[str, str]]:
    augmented = list(history or [])
    topic = command_router.remove_paper_search_command(current_message)
    if topic:
        augmented.append({"role": "user", "content": topic})
    return augmented


def _retrieve_local_documents_for_paper_search(
    query: str,
    top_k: int = 3,
    similarity_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    topic = command_router.remove_paper_search_command(query)
    if not topic:
        return []

    try:
        logger.info("paper search local RAG retrieval started | topic=%s | top_k=%s", topic, top_k)
        documents = rag_service.retrieve_documents(topic, top_k)
        filter_result = rag_service.filter_documents_by_similarity(documents, similarity_threshold)
        filtered = filter_result["filtered_documents"]
        logger.info(
            "paper search local RAG retrieval done | before=%s | after=%s",
            filter_result["original_count"],
            len(filtered),
        )
        return filtered
    except Exception:
        logger.exception("paper search local RAG retrieval failed")
        return []


def _run_paper_search_with_progress(history: List[Dict[str, str]] = None):
    result_queue = queue.Queue(maxsize=1)

    def worker():
        try:
            logger.info("paper search worker started")
            result_queue.put(("result", paper_search_service.search_papers_from_context(history)))
            logger.info("paper search worker finished")
        except Exception as exc:
            logger.exception("paper search worker failed")
            result_queue.put(("error", exc))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    started_at = time.time()
    heartbeat_count = 0
    interval = max(1.0, _paper_search_progress_interval())
    total_timeout = max(interval, _paper_search_total_timeout())

    while True:
        try:
            kind, payload = result_queue.get(timeout=interval)
            if kind == "error":
                raise payload
            return payload
        except queue.Empty:
            heartbeat_count += 1
            elapsed = time.time() - started_at
            if elapsed > total_timeout:
                logger.error("paper search timed out | elapsed=%.2fs", elapsed)
                raise TimeoutError(f"论文检索超时，已等待 {elapsed:.0f} 秒")

            logger.info("paper search still running | elapsed=%.2fs | heartbeat=%s", elapsed, heartbeat_count)
            yield {
                "elapsed": elapsed,
                "heartbeat_count": heartbeat_count,
            }


def _stream_paper_search_for_chat(
    history: List[Dict[str, str]] = None,
    current_message: str = "",
    extra_documents: List[Dict[str, Any]] = None,
):
    logger.info("paper search chat stream started | history_messages=%s", len(history or []))

    augmented_history = _augment_history_for_paper_search(history, current_message)
    search_runner = _run_paper_search_with_progress(augmented_history)
    while True:
        try:
            next(search_runner)
        except StopIteration as stop:
            plan, papers = stop.value
            break

    logger.info("paper search chat stream results ready | queries=%s | paper_count=%s | errors=%s", plan.get("queries", []), len(papers), plan.get("errors", []))

    queries = plan.get("queries", [])
    if queries:
        yield "检索词：\n" + "\n".join([f"- {query}" for query in queries]) + "\n\n"

    if plan.get("errors"):
        yield "部分检索步骤遇到问题，已尽量使用可用结果继续。\n\n"

    if not papers:
        yield "没有检索到可用论文结果，请稍后重试或补充更多上下文。"
        return

    documents = list(extra_documents or []) + paper_search_service.papers_to_documents(papers)
    prompt = _paper_summary_prompt(
        plan,
        papers,
        local_documents=extra_documents or [],
        user_topic=command_router.remove_paper_search_command(current_message),
    )
    logger.info("paper search chat summary started | document_count=%s", len(documents))
    for chunk in rag_service.simple_chat_stream(prompt, documents, history):
        yield chunk
    logger.info("paper search chat stream done")


def _stream_paper_search_for_rag(
    query: str,
    top_k: int = 3,
    history: List[Dict[str, str]] = None,
    similarity_threshold: float = 0.0,
):
    logger.info("paper search rag stream started | history_messages=%s", len(history or []))
    yield {
        "type": "tool_start",
        "tool": "paper_search",
        "content": "",
        "done": False,
    }

    augmented_history = _augment_history_for_paper_search(history, query)
    search_runner = _run_paper_search_with_progress(augmented_history)
    while True:
        try:
            progress = next(search_runner)
            yield {
                "type": "tool_progress",
                "tool": "paper_search",
                "content": "",
                "elapsed": progress["elapsed"],
                "done": False,
            }
        except StopIteration as stop:
            plan, papers = stop.value
            break

    logger.info("paper search rag results ready | queries=%s | paper_count=%s | errors=%s", plan.get("queries", []), len(papers), plan.get("errors", []))

    yield {
        "type": "tool_query",
        "tool": "paper_search",
        "queries": plan.get("queries", []),
        "reason": plan.get("reason", ""),
        "errors": plan.get("errors", []),
        "done": False,
    }

    yield {
        "type": "tool_result",
        "tool": "paper_search",
        "papers": papers,
        "done": False,
    }

    local_query = command_router.remove_paper_search_command(query)
    if not local_query and plan.get("queries"):
        local_query = plan["queries"][0]
    local_documents = _retrieve_local_documents_for_paper_search(local_query, top_k, similarity_threshold)

    yield {
        "type": "retrieval_result",
        "tool": "local_rag",
        "query": local_query,
        "retrieved_documents": local_documents,
        "done": False,
    }

    if not papers and not local_documents:
        yield {
            "type": "error",
            "content": "没有检索到可用论文结果，请稍后重试或补充更多上下文。",
            "done": True,
        }
        return

    documents = local_documents + paper_search_service.papers_to_documents(papers)
    prompt = _paper_summary_prompt(
        plan,
        papers,
        local_documents=local_documents,
        user_topic=command_router.remove_paper_search_command(query),
    )
    full_response = ""
    chunk_count = 0

    logger.info("paper search rag summary started | document_count=%s", len(documents))
    for chunk in rag_service.simple_chat_stream(prompt, documents, history):
        full_response += chunk
        chunk_count += 1
        yield {
            "type": "content",
            "content": chunk,
            "done": False,
        }

    logger.info("paper search rag stream done | chunk_count=%s | chars=%s", chunk_count, len(full_response))
    yield {
        "type": "info",
        "content": "",
        "done": True,
        "paper_search": {
            "queries": plan.get("queries", []),
            "paper_count": len(papers),
            "papers": papers,
            "local_documents": local_documents,
            "errors": plan.get("errors", []),
        },
        "char_count": len(full_response),
        "chunk_count": chunk_count,
    }


class AddDocFromFileRequest(BaseModel):
    file_path: str
    title: str | None = None
    source: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatRequest(BaseModel):
    message: str
    model_type: str = DEFAULT_CHAT_MODEL
    stream: bool = True
    documents: list = None  # 可选的文档列表
    history: list = None  # 可选的历史消息列表


class RAGChatRequest(BaseModel):
    query: str
    model_type: str = DEFAULT_CHAT_MODEL
    top_k: int = 3
    stream: bool = True
    history: list = None  # 可选的历史消息列表
    similarity_threshold: float = 0.0  # 相似度阈值，默认为0.0（不过滤）


class AddJsonDocumentRequest(BaseModel):
    json_data: list  # JSON格式的文档块列表
    title: str  # 文档标题
    source: str | None = None  # 来源信息（可选）


@app.post("/add_document")
def add_document_from_file_api(req: AddDocFromFileRequest):
    try:
        doc_id = add_document_from_file(req.file_path, title=req.title, source=req.source)
        if doc_id is None:
            raise HTTPException(status_code=400, detail="添加失败：请检查文件路径、编码或嵌入/索引配置")
        return {"document_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add_json_document")
def add_json_document_api(req: AddJsonDocumentRequest):
    """
    向知识库添加JSON格式的文档

    Args:
        req: 包含JSON数据、标题和来源的请求对象

    Returns:
        dict: 包含文档ID、块数量和嵌入向量数量的响应
    """
    try:
        # 验证输入数据
        if not req.json_data:
            raise HTTPException(status_code=400, detail="json_data不能为空")

        if not req.title:
            raise HTTPException(status_code=400, detail="title不能为空")

        # 过滤掉空内容的块
        valid_blocks = []
        for i, block in enumerate(req.json_data):
            if not isinstance(block, dict):
                continue

            # 支持多种文本字段名
            content = block.get('text', '') or block.get('content', '') or block.get('chunk_content', '')
            if content and content.strip():
                # 标准化块数据结构
                standardized_block = {
                    'text': content.strip(),
                    'section': block.get('section', block.get('title', f'Section {i + 1}')),
                    'block_id': block.get('block_id', block.get('id', i + 1))
                }
                valid_blocks.append(standardized_block)

        if not valid_blocks:
            raise HTTPException(status_code=400, detail="没有找到有效的文档块")

        # 1. 添加到数据库
        document_id, chunk_ids = _add_json_document_to_database(req.title, valid_blocks, req.source)
        if not document_id:
            raise HTTPException(status_code=500, detail="数据库操作失败")

        # 2. 生成嵌入向量
        embeddings = _generate_embeddings_for_json_blocks(valid_blocks, req.title)

        # 3. 更新FAISS索引（使用chunk_ids作为索引ID）
        if embeddings and chunk_ids:
            # 确保embeddings和chunk_ids数量一致
            if len(embeddings) == len(chunk_ids):
                _update_faiss_index_for_json(embeddings, chunk_ids)
            else:
                # 如果数量不一致，只使用前min(len(embeddings), len(chunk_ids))个
                min_len = min(len(embeddings), len(chunk_ids))
                _update_faiss_index_for_json(embeddings[:min_len], chunk_ids[:min_len])

        return {
            "success": True,
            "document_id": document_id,
            "title": req.title,
            "blocks_count": len(valid_blocks),
            "embeddings_count": len(embeddings),
            "message": f"成功添加文档 '{req.title}'，包含 {len(valid_blocks)} 个块，生成 {len(embeddings)} 个嵌入向量"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加JSON文档失败: {str(e)}")


def _add_json_document_to_database(title: str, blocks: List[Dict[str, Any]], source: str = None,
                                   db_path: str = "local_knowledge.db") -> tuple:
    """
    将JSON文档及其块添加到SQLite数据库
    
    Returns:
        (document_id, chunk_ids): 文档ID和chunk ID列表
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 确保表存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                chunk_content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')

        # 1. 创建主文档记录
        full_content = "\n\n".join([f"## {block.get('section', 'Unknown')}\n{block.get('text', '')}"
                                    for block in blocks if block.get('text', '').strip()])

        cursor.execute(
            "INSERT INTO documents (title, content, source) VALUES (?, ?, ?)",
            (title, full_content, source or title)
        )
        document_id = cursor.lastrowid

        # 2. 添加每个块到document_chunks表，并记录chunk_ids
        chunk_ids = []
        for i, block in enumerate(blocks):
            content = block.get('text', '').strip()
            if content:
                section = block.get('section', 'Unknown')
                chunk_content = f"[{section}] {content}"

                cursor.execute(
                    "INSERT INTO document_chunks (document_id, chunk_content, chunk_index) VALUES (?, ?, ?)",
                    (document_id, chunk_content, i)
                )
                chunk_ids.append(cursor.lastrowid)

        conn.commit()
        conn.close()

        return document_id, chunk_ids

    except Exception as e:
        raise Exception(f"数据库操作失败: {e}")


def _generate_embeddings_for_json_blocks(blocks: List[Dict[str, Any]], title: str) -> List[np.ndarray]:
    """
    为JSON文档块生成嵌入向量
    """
    embeddings = []

    for i, block in enumerate(blocks):
        try:
            content = block.get('text', '').strip()
            if not content:
                continue

            section = block.get('section', 'Unknown')

            # 为嵌入生成包含上下文的文本
            text_for_embedding = f"文档: {title}\n章节: {section}\n内容: {content}"

            embedding = get_embedding(text_for_embedding)

            if embedding is not None:
                embeddings.append(embedding)

        except Exception as e:
            print(f"块 {i + 1} 嵌入生成失败: {e}")

    return embeddings


def _ensure_index_with_idmap(index, dimension: int):
    """
    确保索引是IndexIDMap类型，如果不是则转换
    
    Args:
        index: 现有的FAISS索引
        dimension: 向量维度
        
    Returns:
        包装后的IndexIDMap索引
    """
    # 检查是否是IndexIDMap
    if isinstance(index, faiss.IndexIDMap) or isinstance(index, faiss.IndexIDMap2):
        return index
    
    # 如果是IndexFlatIP，需要转换为IndexIDMap
    if isinstance(index, faiss.IndexFlatIP):
        # 创建新的IndexIDMap
        idmap_index = faiss.IndexIDMap(faiss.IndexFlatIP(dimension))
        
        # 如果原索引有向量，需要迁移（使用顺序ID）
        if index.ntotal > 0:
            # 获取所有向量
            vectors = index.reconstruct_n(0, index.ntotal)
            # 使用顺序ID（0, 1, 2, ...）添加
            ids = np.arange(index.ntotal, dtype=np.int64)
            idmap_index.add_with_ids(vectors, ids)
        
        return idmap_index
    
    # 其他类型，直接包装
    return faiss.IndexIDMap(index)


def _update_faiss_index_for_json(embeddings: List[np.ndarray], chunk_ids: List[int], index_path: str = "faiss_index.index"):
    """
    更新FAISS索引，使用chunk_id作为索引ID，支持直接删除
    
    Args:
        embeddings: 嵌入向量列表
        chunk_ids: 对应的chunk ID列表（用于索引ID映射）
        index_path: 索引文件路径
    """
    try:
        if not embeddings or not chunk_ids:
            return

        # 转换为numpy数组并归一化
        embeddings_array = np.array(embeddings).astype('float32')
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_array = embeddings_array / (norms + 1e-10)

        dimension = embeddings_array.shape[1]
        
        # 检查是否存在现有索引
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
            # 确保是IndexIDMap类型
            index = _ensure_index_with_idmap(index, dimension)
        else:
            # 创建新的IndexIDMap
            base_index = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIDMap(base_index)

        # 将chunk_ids转换为numpy数组
        chunk_ids_array = np.array(chunk_ids, dtype=np.int64)
        
        # 使用chunk_id作为ID添加向量
        index.add_with_ids(embeddings_array, chunk_ids_array)

        # 保存更新后的索引
        faiss.write_index(index, index_path)

    except Exception as e:
        raise Exception(f"FAISS索引更新失败: {e}")


@app.post("/search")
def search(req: SearchRequest):
    try:
        results = rag_service.retrieve_documents(req.query, req.top_k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
def get_all_documents():
    """
    获取所有文档片段信息

    Returns:
        dict: 包含所有文档片段信息的响应
    """
    try:
        conn = sqlite3.connect("local_knowledge.db")
        cursor = conn.cursor()

        # 获取所有文档片段信息
        cursor.execute("""
            SELECT dc.id, dc.document_id, dc.chunk_content, dc.chunk_index,
                   d.title, d.source, d.created_at,
                   LENGTH(dc.chunk_content) as chunk_length
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            ORDER BY d.created_at DESC, dc.chunk_index ASC
        """)

        chunks = []
        for row in cursor.fetchall():
            chunk_id, doc_id, chunk_content, chunk_index, title, source, created_at, chunk_length = row
            # 创建内容预览（前150字符）
            content_preview = chunk_content[:150] + ("..." if len(chunk_content) > 150 else "")

            chunks.append({
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "document_title": title,
                "source": source or "未知",
                "created_at": created_at,
                "chunk_index": chunk_index,
                "chunk_content": chunk_content,
                "chunk_length": chunk_length,
                "content_preview": content_preview
            })

        # 获取统计信息
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM document_chunks")
        total_chunks = cursor.fetchone()[0]

        # 获取FAISS索引信息
        faiss_info = {}
        try:
            if os.path.exists("faiss_index.index"):
                index = faiss.read_index("faiss_index.index")
                faiss_info = {
                    "total_vectors": index.ntotal,
                    "dimension": index.d,
                    "index_type": str(type(index).__name__)
                }
            else:
                faiss_info = {
                    "total_vectors": 0,
                    "dimension": 0,
                    "index_type": "未找到索引文件"
                }
        except Exception as e:
            faiss_info = {
                "total_vectors": 0,
                "dimension": 0,
                "index_type": f"索引读取失败: {str(e)}"
            }

        conn.close()

        return {
            "success": True,
            "chunks": chunks,
            "statistics": {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "faiss_index": faiss_info
            },
            "message": f"成功获取 {len(chunks)} 个文档片段信息"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档片段信息失败: {str(e)}")


@app.get("/documents/{doc_id}")
def get_document_detail(doc_id: int):
    """
    获取指定文档的详细信息

    Args:
        doc_id: 文档ID

    Returns:
        dict: 文档详细信息
    """
    try:
        conn = sqlite3.connect("local_knowledge.db")
        cursor = conn.cursor()

        # 获取文档基本信息
        cursor.execute("""
            SELECT id, title, content, source, created_at
            FROM documents 
            WHERE id = ?
        """, (doc_id,))

        doc_result = cursor.fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail=f"未找到ID为 {doc_id} 的文档")

        doc_id, title, content, source, created_at = doc_result

        # 获取文档块信息
        cursor.execute("""
            SELECT id, chunk_content, chunk_index
            FROM document_chunks 
            WHERE document_id = ?
            ORDER BY chunk_index
        """, (doc_id,))

        chunks = []
        for chunk_row in cursor.fetchall():
            chunk_id, chunk_content, chunk_index = chunk_row
            chunks.append({
                "id": chunk_id,
                "content": chunk_content,
                "index": chunk_index
            })

        conn.close()

        return {
            "success": True,
            "document": {
                "id": doc_id,
                "title": title,
                "content": content,
                "source": source or "未知",
                "created_at": created_at,
                "content_length": len(content),
                "chunks": chunks,
                "chunk_count": len(chunks)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档详情失败: {str(e)}")


def _remove_chunks_from_faiss_index(chunk_ids: List[int], index_path: str = "faiss_index.index"):
    """
    从FAISS索引中删除指定的chunk向量
    
    Args:
        chunk_ids: 要删除的chunk ID列表
        index_path: 索引文件路径
    """
    try:
        if not chunk_ids or not os.path.exists(index_path):
            return
        
        # 读取索引
        index = faiss.read_index(index_path)
        
        # 确保是IndexIDMap类型
        dimension = index.d if hasattr(index, 'd') else 1024
        index = _ensure_index_with_idmap(index, dimension)
        
        # 转换为numpy数组
        chunk_ids_array = np.array(chunk_ids, dtype=np.int64)
        
        # 删除指定的ID
        index.remove_ids(chunk_ids_array)
        
        # 保存更新后的索引
        faiss.write_index(index, index_path)
        
    except Exception as e:
        # 如果删除失败，记录错误但不中断删除流程
        print(f"从FAISS索引删除chunk失败: {e}")


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int):
    """
    删除指定文档，同时删除相关的FAISS索引

    Args:
        doc_id: 文档ID

    Returns:
        dict: 删除结果
    """
    try:
        conn = sqlite3.connect("local_knowledge.db")
        cursor = conn.cursor()

        # 检查文档是否存在
        cursor.execute("SELECT title FROM documents WHERE id = ?", (doc_id,))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"未找到ID为 {doc_id} 的文档")

        title = result[0]

        # 先获取要删除的所有chunk_ids（用于删除FAISS索引）
        cursor.execute("SELECT id FROM document_chunks WHERE document_id = ?", (doc_id,))
        chunk_ids = [row[0] for row in cursor.fetchall()]

        # 删除文档块
        cursor.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
        chunks_deleted = cursor.rowcount

        # 删除主文档
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

        conn.commit()
        conn.close()

        # 从FAISS索引中删除对应的向量
        if chunk_ids:
            _remove_chunks_from_faiss_index(chunk_ids)

        return {
            "success": True,
            "document_id": doc_id,
            "title": title,
            "chunks_deleted": chunks_deleted,
            "faiss_removed": len(chunk_ids),
            "message": f"成功删除文档: {title}，已同步删除FAISS索引中的 {len(chunk_ids)} 个向量"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@app.delete("/chunks/{chunk_id}")
def delete_chunk(chunk_id: int):
    """
    删除指定文档片段，同时删除对应的FAISS索引

    Args:
        chunk_id: 片段ID

    Returns:
        dict: 删除结果
    """
    try:
        conn = sqlite3.connect("local_knowledge.db")
        cursor = conn.cursor()

        # 检查chunk是否存在
        cursor.execute("""
            SELECT dc.id, dc.chunk_content, dc.document_id, d.title 
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.id = ?
        """, (chunk_id,))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"未找到ID为 {chunk_id} 的片段")

        chunk_content = result[1]
        document_id = result[2]
        doc_title = result[3]

        # 删除chunk
        cursor.execute("DELETE FROM document_chunks WHERE id = ?", (chunk_id,))
        
        conn.commit()
        conn.close()

        # 从FAISS索引中删除对应的向量
        _remove_chunks_from_faiss_index([chunk_id])

        return {
            "success": True,
            "chunk_id": chunk_id,
            "document_id": document_id,
            "document_title": doc_title,
            "message": f"成功删除片段，已同步删除FAISS索引中的对应向量"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除片段失败: {str(e)}")


@app.post("/chat")
def simple_chat(req: ChatRequest):
    """普通对话接口，支持文档上传"""
    try:
        # 设置模型类型
        if req.model_type != rag_service.model_type:
            rag_service.switch_model(req.model_type)

        # 处理上传的文档
        documents = None
        if req.documents:
            # 验证和格式化文档数据
            temp_documents = []
            for doc in req.documents:
                if isinstance(doc, dict):
                    # 确保文档包含必要字段
                    formatted_doc = {
                        "title": doc.get("title", "用户上传文档"),
                        "content": doc.get("content", ""),
                        "similarity_score": doc.get("similarity_score", 1.0),
                        "source": doc.get("source", "用户上传")
                    }
                    if formatted_doc["content"].strip():  # 只添加有内容的文档
                        temp_documents.append(formatted_doc)

            # 只有当有有效文档时才设置documents
            if temp_documents:
                documents = temp_documents
        else:
            pass  # 没有收到documents

        # 处理历史记录
        history = None
        if req.history:
            # 验证历史记录格式
            history = []
            for msg in req.history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    if msg["role"] in ["user", "assistant"]:
                        history.append({
                            "role": msg["role"],
                            "content": str(msg["content"])
                        })

        if _paper_search_enabled() and command_router.is_paper_search_command(req.message):
            if req.stream:
                def generate_paper_response():
                    try:
                        for chunk in _stream_paper_search_for_chat(history, req.message, documents):
                            yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

                return StreamingResponse(
                    generate_paper_response(),
                    media_type="text/plain",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )

            response = "".join(_stream_paper_search_for_chat(history, req.message, documents))
            return {"response": response}

        if req.stream:
            # 流式响应
            def generate_response():
                try:
                    for chunk in rag_service.simple_chat_stream(req.message, documents, history):
                        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

            return StreamingResponse(
                generate_response(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 非流式响应
            response_chunks = []
            for chunk in rag_service.simple_chat_stream(req.message, documents, history):
                response_chunks.append(chunk)
            response = "".join(response_chunks)
            return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag_chat")
def rag_chat(req: RAGChatRequest):
    """RAG对话接口"""
    try:
        # 切换模型类型
        if req.model_type != rag_service.model_type:
            rag_service.switch_model(req.model_type)

        # 处理历史记录
        history = None
        if req.history:
            # 验证历史记录格式
            history = []
            for msg in req.history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    if msg["role"] in ["user", "assistant"]:
                        history.append({
                            "role": msg["role"],
                            "content": str(msg["content"])
                        })

        if _paper_search_enabled() and command_router.is_paper_search_command(req.query):
            if req.stream:
                def generate_paper_rag_response():
                    try:
                        for data in _stream_paper_search_for_rag(req.query, req.top_k, history, req.similarity_threshold):
                            yield f"data: {json.dumps(data)}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'done': True})}\n\n"

                return StreamingResponse(
                    generate_paper_rag_response(),
                    media_type="text/plain",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )

            local_documents = _retrieve_local_documents_for_paper_search(req.query, req.top_k, req.similarity_threshold)
            response = "".join(_stream_paper_search_for_chat(history, req.query, local_documents))
            return {"response": response}

        if req.stream:
            # 流式响应 - 增强版，包含详细信息
            def generate_rag_response():
                try:
                    for data in rag_service.rag_chat_stream_with_info(req.query, req.top_k, history,
                                                                      req.similarity_threshold):
                        yield f"data: {json.dumps(data)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'done': True})}\n\n"

            return StreamingResponse(
                generate_rag_response(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 非流式响应（备用，虽然简化版主要支持流式）
            response_chunks = []
            for chunk in rag_service.rag_chat_stream(req.query, req.top_k, history, req.similarity_threshold):
                response_chunks.append(chunk)
            response = "".join(response_chunks)
            return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/status")
def get_system_status():
    """System status endpoint for frontend health checks."""
    try:
        db_path = os.getenv("DB_PATH", "local_knowledge.db")
        index_path = os.getenv("FAISS_INDEX_PATH", "faiss_index.index")

        total_docs = 0
        total_chunks = 0
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            total_chunks = cursor.fetchone()[0]
            conn.close()

        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
            faiss_info = {
                "total_vectors": index.ntotal,
                "dimension": index.d,
                "index_type": str(type(index).__name__),
            }
        else:
            faiss_info = {
                "total_vectors": 0,
                "dimension": 0,
                "index_type": "index_file_not_found",
            }

        return {
            "success": True,
            "system_status": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # Keep these keys for frontend compatibility with old local backend shape.
                "network": {"cloud_available": True, "latency": 0, "bandwidth": 0},
                "complexity_analyzer": {
                    "enabled": False,
                    "total_queries": 0,
                    "current_weights": {},
                    "complexity_stats": {},
                },
                "privacy_detector": {
                    "enabled": False,
                    "keywords_count": 0,
                    "questions_count": 0,
                    "similarity_threshold": 0.0,
                },
                "knowledge_base": {
                    "total_documents": total_docs,
                    "total_chunks": total_chunks,
                    "faiss_index": faiss_info,
                },
                "reranker": {
                    "enabled": reranker.is_rerank_enabled(),
                    "model": reranker.get_current_rerank_model(),
                    "candidate_multiplier": reranker.get_candidate_multiplier(),
                    "max_candidates": reranker.get_max_candidates(),
                },
                "current_model": rag_service.model_type,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=False)
