import os
import sqlite3
from typing import List

import faiss
import numpy as np
from dotenv import load_dotenv
import embedding

DB_PATH = "local_knowledge.db"
INDEX_BASENAME = "faiss_index"  # 对齐现有索引命名，最终文件为 faiss_index.index


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / (norms + 1e-10)


def _load_all_chunks(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT chunk_content
        FROM document_chunks
        ORDER BY id
        """
    )
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def main():
    load_dotenv()

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"未找到数据库文件: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        # 1) 读取所有片段（按 id 升序，匹配默认追加顺序）
        chunks = _load_all_chunks(conn)
        print(f"将基于 {len(chunks)} 个片段重建 FAISS 索引…")

        # 2) 若无片段，写入空索引并退出
        index_path = f"{INDEX_BASENAME}.index"
        if len(chunks) == 0:
            # 创建空索引（使用默认维度 1024）
            dimension = int(os.getenv('DIMENSION', 1024))
            index = faiss.IndexFlatIP(dimension)
            faiss.write_index(index, index_path)
            print(f"已写入空索引: {index_path}")
            return

        # 3) 计算嵌入（批量）
        vectors = embedding.get_embeddings(chunks)
        vectors_np = np.array(vectors, dtype=np.float32)
        vectors_np = _normalize(vectors_np)

        # 4) 以正确维度创建全新索引并写入全部向量
        dimension = int(vectors_np.shape[1])
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors_np)
        faiss.write_index(index, index_path)

        print(
            f"FAISS索引重建完成：{index_path}，共写入向量 {index.ntotal} 条，维度 {dimension}。"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()