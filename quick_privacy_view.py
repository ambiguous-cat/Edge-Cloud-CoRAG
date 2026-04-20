#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速查看隐私关键词和问句
从数据库读取隐私问句并显示对应的嵌入向量
"""

import sys
import os
import sqlite3
import numpy as np
import faiss

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from privacy_detector import create_privacy_detector

def quick_print_all():
    """快速打印所有隐私数据"""
    print("🛡️ 隐私检测系统数据总览")
    print("=" * 60)
    
    # 1. 打印隐私关键词
    print("\n🔑 隐私关键词")
    print("-" * 30)
    
    try:
        db_path = "privacy_data/privacy_data.db"
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT keyword FROM privacy_keywords ORDER BY keyword")
            keywords = cursor.fetchall()
            
            if keywords:
                print(f"总计: {len(keywords)} 个关键词\n")
                for i, (keyword,) in enumerate(keywords, 1):
                    print(f"{i:2d}. {keyword}")
            else:
                print("无关键词数据")
            
            conn.close()
        else:
            print("❌ 数据库文件不存在")
            
    except Exception as e:
        print(f"❌ 读取关键词失败: {e}")
    
    # 2. 打印隐私问句（从数据库读取）
    print_privacy_questions_from_db()
    
    # 3. 打印嵌入向量信息
    print_privacy_embeddings()
    
    # 4. 系统状态
    print_system_status()

def print_privacy_questions_from_db():
    """从数据库读取并打印隐私问句"""
    print("\n💬 隐私问句（从数据库读取）")
    print("-" * 40)
    
    try:
        db_path = "privacy_data/privacy_data.db"
        
        if not os.path.exists(db_path):
            print("❌ 隐私数据库不存在")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询隐私问句表
        cursor.execute("SELECT id, question FROM privacy_questions ORDER BY id")
        questions = cursor.fetchall()
        
        if questions:
            print(f"总计: {len(questions)} 个问句（数据库）\n")
            for question_id, question_text in questions:
                print(f"{question_id:2d}. {question_text}")
        else:
            print("数据库中没有隐私问句")
            
            # 如果数据库为空，尝试从文本文件读取
            print("\n🔄 尝试从文本文件读取...")
            detector = create_privacy_detector()
            if detector.question_mapping:
                print(f"从映射中找到 {len(detector.question_mapping)} 个问句:")
                for i, question in enumerate(detector.question_mapping, 1):
                    print(f"{i:2d}. {question}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 从数据库读取问句失败: {e}")

def print_privacy_embeddings():
    """打印隐私问句的嵌入向量信息"""
    print("\n🔢 隐私问句嵌入向量")
    print("-" * 40)
    
    try:
        # 创建隐私检测器实例
        detector = create_privacy_detector()
        
        if detector.faiss_index is None:
            print("❌ FAISS索引未加载")
            return
        
        index = detector.faiss_index
        questions = detector.question_mapping
        
        print(f"📊 索引统计:")
        print(f"   向量数量: {index.ntotal}")
        print(f"   向量维度: {index.d}")
        print(f"   问句映射: {len(questions)}")
        
        if index.ntotal != len(questions):
            print(f"⚠️  向量数量与问句数量不匹配！")
        
        print(f"\n🔍 向量详情:")
        
        # 显示每个问句及其对应的嵌入向量信息
        for i in range(min(index.ntotal, len(questions), 10)):  # 最多显示10个
            try:
                # 获取向量
                vector = index.reconstruct(i)
                
                # 计算向量统计信息
                vector_norm = np.linalg.norm(vector)
                vector_mean = np.mean(vector)
                vector_std = np.std(vector)
                
                # 获取对应的问句
                question = questions[i] if i < len(questions) else "未知问句"
                
                print(f"\n   问句 {i+1}: {question[:50]}{'...' if len(question) > 50 else ''}")
                print(f"   向量模长: {vector_norm:.6f}")
                print(f"   向量均值: {vector_mean:.6f}")
                print(f"   向量标准差: {vector_std:.6f}")
                print(f"   前5维: {vector[:5].tolist()}")
                
            except Exception as e:
                print(f"   ❌ 获取向量 {i} 失败: {e}")
        
        if index.ntotal > 10:
            print(f"\n   ... 还有 {index.ntotal - 10} 个向量未显示")
        
        # 计算向量间的相似度分析
        if index.ntotal > 1:
            print(f"\n📈 相似度分析:")
            similarities = []
            
            # 计算前5个向量之间的相似度
            sample_size = min(5, index.ntotal)
            for i in range(sample_size):
                for j in range(i+1, sample_size):
                    try:
                        vec_i = index.reconstruct(i)
                        vec_j = index.reconstruct(j)
                        
                        # 计算余弦相似度
                        norm_i = np.linalg.norm(vec_i)
                        norm_j = np.linalg.norm(vec_j)
                        
                        if norm_i > 0 and norm_j > 0:
                            similarity = np.dot(vec_i, vec_j) / (norm_i * norm_j)
                            similarities.append(similarity)
                    except:
                        continue
            
            if similarities:
                print(f"   平均相似度: {np.mean(similarities):.4f}")
                print(f"   最大相似度: {np.max(similarities):.4f}")
                print(f"   最小相似度: {np.min(similarities):.4f}")
        
    except Exception as e:
        print(f"❌ 获取嵌入向量信息失败: {e}")

def print_system_status():
    """打印系统状态"""
    print("\n📊 系统状态")
    print("-" * 30)
    
    files_status = [
        ("数据库", "privacy_data/privacy_data.db"),
        ("问句文件", "privacy_data/privacy_questions.txt"),
        ("索引文件", "privacy_data/privacy_questions.index")
    ]
    
    for name, path in files_status:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"{name}: ✅ 存在 ({size} bytes)")
        else:
            print(f"{name}: ❌ 不存在")

def detailed_view():
    """详细查看模式"""
    print("\n🔍 详细查看模式")
    print("=" * 60)
    
    try:
        detector = create_privacy_detector()
        
        print(f"🔧 检测器配置:")
        print(f"   相似度阈值: {detector.similarity_threshold}")
        print(f"   数据库路径: {detector.privacy_db}")
        print(f"   索引路径: {detector.index_path}")
        
        # 交互式查看特定问句的向量
        while True:
            try:
                index_input = input("\n输入问句索引查看详细向量 (0退出): ").strip()
                if index_input == "0":
                    break
                
                index = int(index_input) - 1
                
                if 0 <= index < len(detector.question_mapping):
                    question = detector.question_mapping[index]
                    print(f"\n问句: {question}")
                    
                    if detector.faiss_index and index < detector.faiss_index.ntotal:
                        vector = detector.faiss_index.reconstruct(index)
                        print(f"完整向量 ({len(vector)}维):")
                        
                        # 分批显示向量
                        batch_size = 10
                        for i in range(0, len(vector), batch_size):
                            batch = vector[i:i+batch_size]
                            print(f"   [{i:3d}-{i+len(batch)-1:3d}]: {batch.tolist()}")
                    else:
                        print("❌ 无法获取对应的向量")
                else:
                    print("❌ 索引超出范围")
                    
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                break
    
    except Exception as e:
        print(f"❌ 详细查看失败: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--detailed":
        detailed_view()
    else:
        quick_print_all()
