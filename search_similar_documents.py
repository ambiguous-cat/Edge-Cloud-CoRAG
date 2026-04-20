import os
import sqlite3
from typing import List, Dict, Any

import faiss
import numpy as np
from dotenv import load_dotenv
import embedding

#单位向量
def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)  # 计算每个向量的L2范数
    return vectors / (norms + 1e-10)  # 添加小量避免除零错误


class DocumentSearcher:

    def __init__(
        self,
        db_path: str = "local_knowledge.db",
        index_path: str = "faiss_index.index",
        embedding_model: str = "text-embedding-3-small",
    ) -> None:

        load_dotenv()

        # 连接数据库
        self._conn = sqlite3.connect(db_path)
        self._cursor = self._conn.cursor()

        # 加载 FAISS 索引
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"未找到FAISS索引文件: {index_path}")
        
        self._index = faiss.read_index(index_path)

        # 预加载映射：索引位置 -> 片段元数据
        self._pos_to_chunk: List[Dict[str, Any]] = self._load_chunk_mapping()

    def _load_chunk_mapping(self) -> List[Dict[str, Any]]:
        """加载文档片段映射表，建立索引位置与片段元数据的对应关系。

        返回:
            映射列表，其中每个元素是包含片段元数据的字典
        """
        # 取出所有片段，按 id 升序（与默认追加顺序一致）
        self._cursor.execute(
            """
            SELECT dc.id, dc.document_id, dc.chunk_content, dc.chunk_index, d.title
            FROM document_chunks AS dc
            JOIN documents AS d ON dc.document_id = d.id
            ORDER BY dc.id
            """
        )
        rows = self._cursor.fetchall()

        # 与索引向量数对齐
        ntotal = int(self._index.ntotal)
        if len(rows) < ntotal:
            # DB 少于索引，裁剪索引可见范围
            rows = rows[:ntotal]
        elif len(rows) > ntotal:
            # DB 多于索引，裁剪到索引长度
            rows = rows[:ntotal]

        mapping: List[Dict[str, Any]] = []
        for chunk_id, doc_id, content, chunk_index, title in rows:
            mapping.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "title": title,
                    "chunk_index": chunk_index,
                    "content": content,
                }
            )
        return mapping

    def _embed_and_normalize_query(self, text: str) -> np.ndarray:
        """将查询文本转换为归一化的嵌入向量。

        参数:
            text: 查询文本

        返回:
            归一化后的查询向量，形状为 [1, d]
        """
        try:
            vec = embedding.get_embedding(text)
            vec_np = np.array([vec], dtype=np.float32)
            vec_np = _normalize_vectors(vec_np)
            return vec_np
        except Exception as e:
            print("生成嵌入或转numpy时出错:", e)
            raise

    def search_similar_documents(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索与查询文本相似的文档片段。

        参数:
            query_text: 查询文本
            top_k: 返回的最相似结果数量

        返回:
            包含相似文档片段信息的字典列表，按相似度降序排列
        """
        if not query_text or top_k <= 0:
            return []

        # 计算查询向量并检索
        query_vec = self._embed_and_normalize_query(query_text)
        similarity_scores, indices = self._index.search(query_vec, top_k)

        #降维
        scores = similarity_scores[0]
        idxs = indices[0]

        results: List[Dict[str, Any]] = []
        for rank, (idx, score) in enumerate(zip(idxs.tolist(), scores.tolist()), start=1):
            if idx < 0:
                continue  # FAISS 可能返回 -1 表示无结果
            if idx >= len(self._pos_to_chunk):
                continue

            meta = self._pos_to_chunk[idx]
            results.append(
                {
                    "rank": rank,
                    "chunk_id": meta["chunk_id"],
                    "doc_id": meta["doc_id"],
                    "title": meta["title"],
                    "chunk_index": meta["chunk_index"],
                    "content": meta["content"],
                    "similarity_score": float(score),  # 内积值，等价于归一化后的余弦相似度
                }
            )

        return results

    def close(self) -> None:
        """关闭数据库连接，释放资源。"""
        try:
            if self._conn:
                self._conn.close()
        finally:
            self._conn = None
            self._cursor = None


