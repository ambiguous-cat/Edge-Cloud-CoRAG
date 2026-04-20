#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试相似度超过1的问题
检查FAISS索引中向量的归一化状态
"""

import numpy as np
import faiss
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_similar_documents import DocumentSearcher, _normalize_vectors
from embedding import get_embedding

def check_vector_normalization():
    """检查FAISS索引中向量的归一化状态"""
    print("🔍 检查FAISS索引中向量的归一化状态")
    print("=" * 50)
    
    try:
        # 加载FAISS索引
        if not os.path.exists("faiss_index.index"):
            print("❌ 未找到FAISS索引文件")
            return
            
        index = faiss.read_index("faiss_index.index")
        print(f"✅ 成功加载索引，包含 {index.ntotal} 个向量，维度 {index.d}")
        
        if index.ntotal == 0:
            print("⚠️ 索引为空")
            return
        
        # 检查前几个向量的模长
        print("\n📏 检查向量模长:")
        sample_size = min(10, index.ntotal)
        
        norms = []
        for i in range(sample_size):
            vector = index.reconstruct(i)
            norm = np.linalg.norm(vector)
            norms.append(norm)
            print(f"向量 {i}: 模长 = {norm:.6f}")
        
        avg_norm = np.mean(norms)
        print(f"\n📊 统计信息:")
        print(f"平均模长: {avg_norm:.6f}")
        print(f"最大模长: {max(norms):.6f}")
        print(f"最小模长: {min(norms):.6f}")
        
        # 判断是否归一化
        if abs(avg_norm - 1.0) < 0.01:
            print("✅ 向量已正确归一化")
        else:
            print("❌ 向量未正确归一化！")
            print("   这解释了为什么相似度会超过1")
            
        return norms
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return None

def test_similarity_calculation():
    """测试相似度计算过程"""
    print("\n🧪 测试相似度计算过程")
    print("=" * 50)
    
    try:
        searcher = DocumentSearcher()
        
        # 测试查询
        query = "机器学习"
        print(f"🔎 测试查询: '{query}'")
        
        # 获取查询向量
        query_embedding = get_embedding(query)
        if query_embedding is None:
            print("❌ 无法获取查询向量")
            return
            
        query_vec = np.array([query_embedding], dtype=np.float32)
        print(f"原始查询向量模长: {np.linalg.norm(query_vec):.6f}")
        
        # 归一化查询向量
        query_vec_normalized = _normalize_vectors(query_vec)
        print(f"归一化后查询向量模长: {np.linalg.norm(query_vec_normalized):.6f}")
        
        # 执行搜索
        results = searcher.search_similar_documents(query, top_k=3)
        
        if results:
            print(f"\n📋 搜索结果:")
            for i, result in enumerate(results):
                score = result['similarity_score']
                print(f"结果 {i+1}: 相似度 = {score:.6f}")
                
                # 如果相似度超过1，这是问题所在
                if score > 1.0:
                    print(f"   ⚠️ 相似度超过1！这表明索引中的向量未正确归一化")
        
        searcher.close()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def diagnose_problem():
    """诊断问题并提供解决方案"""
    print("\n🔧 问题诊断和解决方案")
    print("=" * 50)
    
    print("🔍 可能的原因:")
    print("1. FAISS索引中的向量未正确归一化")
    print("2. 向量在添加到索引时没有经过归一化处理")
    print("3. 使用了错误的FAISS索引类型")
    
    print("\n💡 解决方案:")
    print("1. 重建FAISS索引，确保所有向量都经过归一化")
    print("2. 检查add_document_from_file.py中的向量处理")
    print("3. 检查add_json_papers.py中的向量处理")
    
    print("\n🛠️ 修复步骤:")
    print("1. 运行 python rebuild_faiss_index.py")
    print("2. 确保所有嵌入向量在添加到索引前都经过归一化")
    print("3. 重新测试相似度计算")

def check_embedding_normalization():
    """检查嵌入向量生成时的归一化"""
    print("\n🔬 检查嵌入向量生成")
    print("=" * 50)
    
    try:
        # 测试几个文本的嵌入向量
        test_texts = [
            "机器学习算法",
            "深度学习神经网络",
            "数据挖掘技术"
        ]
        
        for text in test_texts:
            embedding_vec = get_embedding(text)
            if embedding_vec is not None:
                norm = np.linalg.norm(embedding_vec)
                print(f"'{text}' -> 模长: {norm:.6f}")
                
                if abs(norm - 1.0) > 0.01:
                    print(f"   ⚠️ 此向量未归一化！")
            else:
                print(f"'{text}' -> 获取嵌入失败")
                
    except Exception as e:
        print(f"❌ 检查嵌入向量失败: {e}")

def main():
    """主函数"""
    print("🚨 相似度超过1的问题调试")
    print("=" * 60)
    
    # 1. 检查FAISS索引中向量的归一化状态
    norms = check_vector_normalization()
    
    # 2. 检查嵌入向量生成时的归一化
    check_embedding_normalization()
    
    # 3. 测试相似度计算过程
    test_similarity_calculation()
    
    # 4. 诊断问题并提供解决方案
    diagnose_problem()
    
    print("\n" + "=" * 60)
    if norms and max(norms) > 1.01:
        print("🔴 确认问题: FAISS索引中的向量未正确归一化")
        print("📝 建议: 重建FAISS索引以修复此问题")
    else:
        print("🟡 需要进一步调查相似度计算逻辑")

if __name__ == "__main__":
    main()
