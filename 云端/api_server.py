from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from search_similar_documents import DocumentSearcher
from add_document_from_file import add_document_from_file
from rag_chat import RAGChatService
import chat_model
import json
import sqlite3
import numpy as np
from typing import List, Dict, Any
from embedding import get_embedding, get_embeddings
import faiss
import os
import time
import requests

app = FastAPI(title="RAG系统API", description="支持文档管理、检索和对话功能")
searcher = DocumentSearcher()

# 创建RAG服务实例 - 复用searcher避免重复初始化
rag_service = RAGChatService(searcher=searcher, model_type="glm-4")


# 网络监控类
class NetworkMonitor:
    @staticmethod
    def get_status():
        """获取网络状态"""
        try:
            # 测试云端连接
            start_time = time.time()
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            latency = (time.time() - start_time) * 1000  # 转换为毫秒

            if response.status_code == 200:
                return {
                    "cloud_available": True,
                    "latency": latency,
                    "bandwidth": 100  # 假设带宽，实际项目中可以测量
                }
            else:
                return {
                    "cloud_available": False,
                    "latency": 0,
                    "bandwidth": 0
                }
        except:
            return {
                "cloud_available": False,
                "latency": 0,
                "bandwidth": 0
            }


# 创建网络监控器
network_monitor = NetworkMonitor()


class AddDocFromFileRequest(BaseModel):
    file_path: str
    title: str | None = None
    source: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatRequest(BaseModel):
    message: str
    model_type: str = "deepseek-r1:1.5b"
    stream: bool = True
    documents: list = None  # 可选的文档列表
    history: list = None  # 可选的历史消息列表


class RAGChatRequest(BaseModel):
    query: str
    model_type: str = "deepseek-r1:1.5b"
    top_k: int = 3
    stream: bool = True
    history: list = None  # 可选的历史消息列表
    similarity_threshold: float = 0.0  # 相似度阈值，默认为0.0（不过滤）


class PrivacyCheckRequest(BaseModel):
    chat_history: list  # 聊天历史记录
    get_details: bool = False  # 是否返回详细信息


class KeywordAddRequest(BaseModel):
    keyword: str


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
        results = searcher.search_similar_documents(req.query, req.top_k)
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


def warm_up_model():
    """预热模型，避免首次请求的冷启动延迟"""
    print("🔥 开始预热Ollama模型...")
    try:
        import requests
        import time

        # 发送一个简单的预热请求
        warmup_start = time.time()
        url = "http://localhost:11434/api/generate"
        data = {
            "model": "qwen3:1.7b",
            "prompt": "Hello",
            "stream": False,
            "options": {
                "num_predict": 1,  # 只生成1个token
                "temperature": 0.1
            }
        }

        response = requests.post(url, json=data, timeout=60)
        warmup_time = time.time() - warmup_start

        if response.status_code == 200:
            print(f"✅ 模型预热完成，耗时: {warmup_time:.2f}秒")
        else:
            print(f"⚠️ 模型预热失败: HTTP {response.status_code}")

    except Exception as e:
        print(f"⚠️ 模型预热出错: {e}")
        print("   这可能不会影响正常功能，但首次请求可能较慢")


if __name__ == "__main__":
    import uvicorn

    # 预热模型
    warm_up_model()

    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=False)