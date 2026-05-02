#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON格式论文导入脚本
用于将JSON格式的拆分论文添加到知识库并完成嵌入
"""

import json
import os
import sqlite3
import numpy as np
from typing import List, Dict, Any
from embedding import get_embedding
import faiss

def load_json_paper(json_file_path: str) -> List[Dict[str, Any]]:
    """
    加载JSON格式的论文文件
    
    Args:
        json_file_path: JSON文件路径
        
    Returns:
        List[Dict]: 文档块列表
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ 成功加载JSON文件: {json_file_path}")
        print(f"📄 包含 {len(data)} 个文档块")
        
        return data
    except Exception as e:
        print(f"❌ 加载JSON文件失败: {e}")
        return []


def add_paper_to_database(paper_title: str, paper_blocks: List[Dict[str, Any]], source: str = None, db_path: str = "local_knowledge.db") -> int:
    """
    将论文及其块添加到SQLite数据库
    
    Args:
        paper_title: 论文标题
        paper_blocks: 论文块列表
        source: 来源信息
        db_path: 数据库路径
        
    Returns:
        int: 插入的文档ID，失败返回None
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
        
        # 1. 首先创建主文档记录
        # 将所有块的内容合并作为完整文档内容
        full_content = "\n\n".join([f"## {block.get('section', 'Unknown')}\n{block.get('content', '')}" 
                                   for block in paper_blocks if block.get('content', '').strip()])
        
        cursor.execute(
            "INSERT INTO documents (title, content, source) VALUES (?, ?, ?)",
            (paper_title, full_content, source or paper_title)
        )
        document_id = cursor.lastrowid
        
        print(f"📄 创建主文档记录，ID: {document_id}")
        
        # 2. 然后添加每个块到document_chunks表
        chunk_ids = []
        for i, block in enumerate(paper_blocks):
            content = block.get('text', '').strip()  # JSON中使用的是'text'字段
            if content:
                # 为块内容添加section信息
                section = block.get('section', 'Unknown')
                block_id = block.get('block_id', i + 1)
                
                chunk_content = f"[{section}] {content}"
                
                cursor.execute(
                    "INSERT INTO document_chunks (document_id, chunk_content, chunk_index) VALUES (?, ?, ?)",
                    (document_id, chunk_content, i)
                )
                chunk_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        
        print(f"💾 成功添加论文到数据库")
        print(f"   - 主文档ID: {document_id}")
        print(f"   - 文档块数量: {len(chunk_ids)}")
        print(f"   - 块ID范围: {min(chunk_ids) if chunk_ids else 'N/A'}-{max(chunk_ids) if chunk_ids else 'N/A'}")
        
        return document_id
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        return None

def generate_embeddings_for_chunks(paper_blocks: List[Dict[str, Any]], paper_title: str) -> List[np.ndarray]:
    """
    为论文块生成嵌入向量
    
    Args:
        paper_blocks: 论文块列表
        paper_title: 论文标题
        
    Returns:
        List[np.ndarray]: 嵌入向量列表
    """
    embeddings = []
    
    print("🔄 开始为文档块生成嵌入向量...")
    
    for i, block in enumerate(paper_blocks):
        try:
            content = block.get('text', '').strip()
            if not content:
                continue
                
            section = block.get('section', 'Unknown')
            block_id = block.get('block_id', i + 1)
            
            # 为嵌入生成包含上下文的文本
            text_for_embedding = f"论文: {paper_title}\n章节: {section}\n内容: {content}"
            
            embedding = get_embedding(text_for_embedding)
            
            if embedding is not None:
                embeddings.append(embedding)
                print(f"✅ 块 {i+1}/{len(paper_blocks)} ({section}) 嵌入完成")
            else:
                print(f"⚠️ 块 {i+1} 嵌入失败，跳过")
                
        except Exception as e:
            print(f"❌ 块 {i+1} 嵌入出错: {e}")
    
    print(f"🎯 成功生成 {len(embeddings)} 个嵌入向量")
    return embeddings

def update_faiss_index(embeddings: List[np.ndarray], document_ids: List[int], index_path: str = "faiss_index.index"):
    """
    更新FAISS索引
    
    Args:
        embeddings: 嵌入向量列表
        document_ids: 对应的文档ID列表
        index_path: 索引文件路径
    """
    try:
        if not embeddings:
            print("⚠️ 没有嵌入向量，跳过索引更新")
            return
        
        # 转换为numpy数组
        embeddings_array = np.array(embeddings).astype('float32')
        
        # 归一化向量（关键修复！）
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_array = embeddings_array / (norms + 1e-10)  # 添加小量避免除零错误
        print(f"🔄 向量已归一化，平均模长: {np.mean(np.linalg.norm(embeddings_array, axis=1)):.6f}")
        
        # 检查是否存在现有索引
        if os.path.exists(index_path):
            print("📂 加载现有FAISS索引...")
            index = faiss.read_index(index_path)
        else:
            print("🆕 创建新的FAISS索引...")
            dimension = embeddings_array.shape[1]
            index = faiss.IndexFlatIP(dimension)  # 使用内积相似度
        
        # 添加新的嵌入向量
        index.add(embeddings_array)
        
        # 保存更新后的索引
        faiss.write_index(index, index_path)
        
        print(f"💾 FAISS索引已更新，当前包含 {index.ntotal} 个向量")
        
    except Exception as e:
        print(f"❌ FAISS索引更新失败: {e}")

def import_json_paper(json_file_path: str, paper_title: str = None, source: str = None):
    """
    导入JSON格式的论文到知识库
    
    Args:
        json_file_path: JSON文件路径
        paper_title: 论文标题（如果不提供，将使用文件名）
        source: 来源信息
    """
    print(f"🚀 开始导入JSON论文: {json_file_path}")
    
    # 如果没有提供标题，使用文件名
    if not paper_title:
        paper_title = os.path.splitext(os.path.basename(json_file_path))[0]
    
    # 1. 加载JSON文件
    blocks = load_json_paper(json_file_path)
    if not blocks:
        print("❌ 导入失败：无法加载JSON文件")
        return
    
    # 过滤掉空内容的块
    valid_blocks = [block for block in blocks if block.get('text', '').strip()]
    if not valid_blocks:
        print("❌ 导入失败：没有有效的文档块")
        return
    
    print(f"📝 有效文档块: {len(valid_blocks)}")
    
    # 2. 添加到数据库（正确的表结构）
    document_id = add_paper_to_database(paper_title, valid_blocks, source)
    if not document_id:
        print("❌ 导入失败：数据库操作失败")
        return
    
    # 3. 生成嵌入向量（为每个块生成）
    embeddings = generate_embeddings_for_chunks(valid_blocks, paper_title)
    
    # 4. 更新FAISS索引
    if embeddings:
        # 为FAISS索引创建虚拟的chunk_ids（基于document_id和块索引）
        chunk_ids = [document_id * 1000 + i for i in range(len(embeddings))]
        update_faiss_index(embeddings, chunk_ids)
        
        print(f"🎉 成功导入论文: {paper_title}")
        print(f"📊 统计信息:")
        print(f"   - 主文档ID: {document_id}")
        print(f"   - 文档块数量: {len(valid_blocks)}")
        print(f"   - 嵌入向量: {len(embeddings)}")
        print(f"   - FAISS索引已更新")
    else:
        print("⚠️ 没有生成嵌入向量，但文档已保存到数据库")

def import_all_json_papers(folder_path: str = "语料"):
    """
    导入指定文件夹中的所有JSON论文
    
    Args:
        folder_path: 包含JSON文件的文件夹路径
    """
    print(f"📁 扫描文件夹: {folder_path}")
    
    if not os.path.exists(folder_path):
        print(f"❌ 文件夹不存在: {folder_path}")
        return
    
    json_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.json')]
    
    if not json_files:
        print("❌ 文件夹中没有找到JSON文件")
        return
    
    print(f"📄 找到 {len(json_files)} 个JSON文件")
    
    for i, json_file in enumerate(json_files):
        print(f"\n{'='*50}")
        print(f"处理文件 {i+1}/{len(json_files)}: {json_file}")
        print(f"{'='*50}")
        
        json_path = os.path.join(folder_path, json_file)
        import_json_paper(json_path)
    
    print(f"\n🎊 所有JSON论文导入完成！")

if __name__ == "__main__":
    print("📚 JSON论文导入工具")
    print("="*50)
    
    # 选择导入方式
    choice = input("选择导入方式:\n1. 导入单个JSON文件\n2. 导入语料文件夹中的所有JSON文件\n请输入选择 (1/2): ").strip()
    
    if choice == "1":
        # 单个文件导入
        json_path = input("请输入JSON文件路径: ").strip()
        if json_path and os.path.exists(json_path):
            paper_title = input("请输入论文标题 (留空使用文件名): ").strip()
            source = input("请输入来源信息 (可选): ").strip()
            
            import_json_paper(
                json_path, 
                paper_title if paper_title else None,
                source if source else None
            )
        else:
            print("❌ 文件路径无效")
    
    elif choice == "2":
        # 批量导入
        folder_path = input("请输入文件夹路径 (留空使用默认'语料'文件夹): ").strip()
        if not folder_path:
            folder_path = "语料"
        
        import_all_json_papers(folder_path)
    
    else:
        print("❌ 无效选择")
    
    print("\n👋 导入完成，感谢使用！")
