import os
import sqlite3
import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import embedding
import re

# 加载环境变量
load_dotenv()

# 自定义文本分段函数
def split_text_by_double_newline(text):
    """
    按连续两个换行符分割文本
    
    参数:
        text: 要分割的文本
    
    返回:
        chunks: 分割后的文本片段列表
    """
    # 使用正则表达式按连续两个或更多换行符分割
    # \n\n+ 匹配两个或更多连续的换行符
    chunks = re.split(r'\n\n+', text.strip())
    
    # 过滤空片段并清理每个片段
    cleaned_chunks = []
    for chunk in chunks:
        # 移除片段首尾的空白字符
        cleaned_chunk = chunk.strip()
        # 只保留非空片段
        if cleaned_chunk:
            cleaned_chunks.append(cleaned_chunk)
    
    # 如果没有找到分段标记，将整个文本作为一个片段
    if not cleaned_chunks:
        cleaned_chunks = [text.strip()]
    
    print(f"文档已按双换行符分为 {len(cleaned_chunks)} 个片段")
    return cleaned_chunks

# 向量归一化函数
def normalize(vecs):
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / (norms + 1e-10)

# 初始化SQLite数据库
def init_database(db_path="local_knowledge.db"):
    """初始化SQLite数据库，创建文档表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建文档表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建文档片段表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        chunk_content TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"数据库已初始化: {db_path}")
    return db_path

# 初始化FAISS向量存储
def init_faiss_index(index_path="faiss_index"):
    """初始化FAISS索引（余弦相似度）"""
    # 检查索引是否已存在
    if os.path.exists(f"{index_path}.index"):
        print(f"FAISS索引已存在: {index_path}.index")
        return index_path
    
    # 创建新的FAISS
    dimension = int(os.getenv('DIMENSION', 1024))
    print(dimension)
    # 使用内积（IP）索引，配合归一化实现余弦相似度
    index = faiss.IndexFlatIP(dimension)
    
    # 保存索引
    faiss.write_index(index, f"{index_path}.index")
    print(f"FAISS索引已创建: {index_path}.index")
    return index_path

# 添加文档到本地知识库
def add_document_to_knowledge(title, content, source=None, db_path="local_knowledge.db", index_path="faiss_index"):
    """添加文档到本地知识库"""
    # 1. 存储文档到SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 插入文档
    cursor.execute("INSERT INTO documents (title, content, source) VALUES (?, ?, ?)", (title, content, source))
    document_id = cursor.lastrowid
    
    # 2. 分割文档 - 按连续两个换行符分段
    chunks = split_text_by_double_newline(content)
    
    # 3. 生成嵌入向量并存储到FAISS
    # print(chunks[0])
    # chunk_embeddings = []
    # for chunk in chunks:
    #     chunk_embeddings.append(embedding.get_ollama_embedding(chunk))
    chunk_embeddings = embedding.get_embeddings(chunks)
    chunk_embeddings = normalize(np.array(chunk_embeddings, dtype=np.float32))  # 归一化
    
    # 加载FAISS索引
    index = faiss.read_index(f"{index_path}.index")
    
    # 添加向量到索引
    index.add(chunk_embeddings)
    
    # 保存更新后的索引
    faiss.write_index(index, f"{index_path}.index")
    
    # 4. 存储文档片段到SQLite
    for i, chunk in enumerate(chunks):
        cursor.execute(
            "INSERT INTO document_chunks (document_id, chunk_content, chunk_index) VALUES (?, ?, ?)",
            (document_id, chunk, i)
        )
    
    conn.commit()
    conn.close()
    
    print(f"文档 '{title}' 已添加到知识库，分为 {len(chunks)} 个片段")
    return document_id

# 主函数
if __name__ == "__main__":
    # 初始化数据库
    db_path = init_database()

    # 初始化FAISS索引
    irendex_path = init_faiss_index()