#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import numpy as np
import faiss
import os
from typing import Optional, List, Tuple

def load_faiss_index(index_path: str = "faiss_index.index") -> Optional[faiss.Index]:
    """加载FAISS索引"""
    try:
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
            print(f"✅ 成功加载FAISS索引: {index.ntotal} 个向量")
            return index
        else:
            print(f"⚠️ FAISS索引文件不存在: {index_path}")
            return None
    except Exception as e:
        print(f"❌ 加载FAISS索引失败: {e}")
        return None

def get_embedding_info(doc_id: int, faiss_index: Optional[faiss.Index]) -> dict:
    """获取文档的嵌入向量信息"""
    info = {
        "has_embedding": False,
        "vector_dimension": 0,
        "vector_norm": 0.0,
        "vector_preview": None
    }
    
    if faiss_index is None:
        return info
    
    try:
        # 假设文档ID对应FAISS索引中的位置（这个映射可能需要根据实际情况调整）
        if doc_id <= faiss_index.ntotal:
            # 获取向量
            vector = faiss_index.reconstruct(doc_id - 1)  # FAISS索引从0开始
            
            info["has_embedding"] = True
            info["vector_dimension"] = len(vector)
            info["vector_norm"] = float(np.linalg.norm(vector))
            info["vector_preview"] = vector[:5].tolist()  # 显示前5个维度
            
    except Exception as e:
        print(f"⚠️ 获取文档 {doc_id} 的嵌入向量失败: {e}")
    
    return info

def print_document_chunks(cursor, doc_id: int, show_content: bool = False, max_chunks: int = 5):
    """打印文档的片段信息"""
    try:
        # 查询文档片段
        if show_content:
            cursor.execute("""
                SELECT id, chunk_content, LENGTH(chunk_content) as char_count
                FROM document_chunks 
                WHERE document_id = ? 
                ORDER BY chunk_index 
                LIMIT ?
            """, (doc_id, max_chunks))
        else:
            cursor.execute("""
                SELECT id, LENGTH(chunk_content) as char_count
                FROM document_chunks 
                WHERE document_id = ? 
                ORDER BY chunk_index 
                LIMIT ?
            """, (doc_id, max_chunks))
        
        chunks = cursor.fetchall()
        
        if chunks:
            print(f"  📄 文档片段 (显示前{min(len(chunks), max_chunks)}个):")
            for i, chunk in enumerate(chunks):
                if show_content:
                    chunk_id, content, char_count = chunk
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"    片段ID {chunk_id}: {char_count}字符")
                    print(f"    内容预览: {preview}")
                else:
                    chunk_id, char_count = chunk
                    print(f"    片段ID {chunk_id}: {char_count}字符")
                
                if i < len(chunks) - 1:
                    print()
        
        # 如果还有更多片段，显示提示
        cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (doc_id,))
        total_chunks = cursor.fetchone()[0]
        if total_chunks > max_chunks:
            print(f"    ... 还有 {total_chunks - max_chunks} 个片段")
            
    except Exception as e:
        print(f"    ❌ 查询片段失败: {e}")

def print_all_documents(show_embeddings: bool = True, show_content: bool = False, max_chunks_per_doc: int = 3):
    """
    打印数据库中的所有文档及其嵌入向量信息
    
    Args:
        show_embeddings: 是否显示嵌入向量信息
        show_content: 是否显示片段内容预览
        max_chunks_per_doc: 每个文档最多显示的片段数量
    """
    print("📚 数据库中的所有文档")
    print("=" * 80)
    
    # 加载FAISS索引
    faiss_index = None
    if show_embeddings:
        faiss_index = load_faiss_index()
    
    try:
        conn = sqlite3.connect("local_knowledge.db")
        cursor = conn.cursor()
        
        # 查询所有文档
        cursor.execute("SELECT id, title, source, created_at FROM documents ORDER BY id")
        documents = cursor.fetchall()
        
        if not documents:
            print("📭 数据库中没有文档")
            return
        
        print(f"📊 总共 {len(documents)} 个文档:\n")
        
        for doc_id, title, source, created_at in documents:
            print(f"🆔 ID: {doc_id}")
            print(f"📝 标题: {title}")
            print(f"📂 来源: {source}")
            print(f"🕐 创建时间: {created_at}")
            
            # 查询文档片段数量
            cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (doc_id,))
            chunk_count = cursor.fetchone()[0]
            print(f"📄 片段数量: {chunk_count}")
            
            # 显示嵌入向量信息
            if show_embeddings:
                embedding_info = get_embedding_info(doc_id, faiss_index)
                print(f"🔢 嵌入向量:")
                if embedding_info["has_embedding"]:
                    print(f"  ✅ 已生成嵌入向量")
                    print(f"  📏 维度: {embedding_info['vector_dimension']}")
                    print(f"  📐 向量模长: {embedding_info['vector_norm']:.4f}")
                    print(f"  👀 前5维预览: {embedding_info['vector_preview']}")
                else:
                    print(f"  ❌ 未找到嵌入向量")
            
            # 显示片段信息
            if chunk_count > 0:
                print_document_chunks(cursor, doc_id, show_content, max_chunks_per_doc)
            
            print("=" * 80)
        
        conn.close()
        
        # 显示FAISS索引统计信息
        if faiss_index:
            print(f"\n🔍 FAISS索引统计:")
            print(f"  总向量数: {faiss_index.ntotal}")
            print(f"  向量维度: {faiss_index.d}")
        
    except Exception as e:
        print(f"❌ 查询数据库时出错: {e}")

def print_embedding_statistics():
    """打印嵌入向量统计信息"""
    print("\n📊 嵌入向量统计分析")
    print("=" * 50)
    
    faiss_index = load_faiss_index()
    if faiss_index is None:
        print("❌ 无法加载FAISS索引")
        return
    
    try:
        # 获取所有向量
        all_vectors = []
        for i in range(faiss_index.ntotal):
            vector = faiss_index.reconstruct(i)
            all_vectors.append(vector)
        
        if all_vectors:
            vectors_array = np.array(all_vectors)
            
            print(f"📈 统计信息:")
            print(f"  向量数量: {len(all_vectors)}")
            print(f"  向量维度: {vectors_array.shape[1]}")
            print(f"  平均模长: {np.mean([np.linalg.norm(v) for v in all_vectors]):.4f}")
            print(f"  最大模长: {np.max([np.linalg.norm(v) for v in all_vectors]):.4f}")
            print(f"  最小模长: {np.min([np.linalg.norm(v) for v in all_vectors]):.4f}")
            
            # 计算向量间的平均相似度
            if len(all_vectors) > 1:
                similarities = []
                for i in range(min(10, len(all_vectors))):  # 只计算前10个向量的相似度
                    for j in range(i+1, min(10, len(all_vectors))):
                        sim = np.dot(all_vectors[i], all_vectors[j]) / (
                            np.linalg.norm(all_vectors[i]) * np.linalg.norm(all_vectors[j])
                        )
                        similarities.append(sim)
                
                if similarities:
                    print(f"  平均余弦相似度: {np.mean(similarities):.4f}")
        
    except Exception as e:
        print(f"❌ 统计分析失败: {e}")

if __name__ == "__main__":
    print("🔍 文档和嵌入向量查看器")
    print("=" * 50)
    
    # 交互式选择
    print("选择查看模式:")
    print("1. 基本信息（不显示嵌入向量）")
    print("2. 完整信息（包含嵌入向量）")
    print("3. 详细信息（包含内容预览）")
    print("4. 嵌入向量统计分析")
    
    choice = input("请输入选择 (1-4): ").strip()
    
    if choice == "1":
        print_all_documents(show_embeddings=False, show_content=False)
    elif choice == "2":
        print_all_documents(show_embeddings=True, show_content=False)
    elif choice == "3":
        print_all_documents(show_embeddings=True, show_content=True, max_chunks_per_doc=5)
    elif choice == "4":
        print_embedding_statistics()
    else:
        print("❌ 无效选择，使用默认模式")
        print_all_documents(show_embeddings=True, show_content=False)
