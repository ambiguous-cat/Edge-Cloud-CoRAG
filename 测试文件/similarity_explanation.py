#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相似度计算原理和区间说明
详细解释检索系统中相似度的计算方式和数值含义
"""

import numpy as np
import faiss
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_similar_documents import DocumentSearcher, _normalize_vectors
from embedding import get_embedding

def explain_similarity_calculation():
    """详细解释相似度计算原理"""
    print("🔍 检索相似度计算原理详解")
    print("=" * 60)
    
    print("\n📊 1. 相似度计算方式")
    print("-" * 30)
    print("本系统使用 **余弦相似度** 来计算文档相似性")
    print()
    print("🔢 计算公式:")
    print("   cos_similarity(A, B) = (A · B) / (||A|| × ||B||)")
    print("   其中:")
    print("   - A · B 是向量A和B的点积（内积）")
    print("   - ||A|| 是向量A的L2范数（模长）")
    print("   - ||B|| 是向量B的L2范数（模长）")
    
    print("\n🛠️ 2. 实现方式")
    print("-" * 30)
    print("为了高效计算，系统采用以下策略:")
    print("1. **向量归一化**: 将所有向量归一化为单位向量")
    print("2. **内积计算**: 使用FAISS的IndexFlatIP（内积索引）")
    print("3. **等价性**: 归一化向量的内积 = 余弦相似度")
    
    print("\n📈 3. 相似度数值区间")
    print("-" * 30)
    print("余弦相似度的取值范围: [-1, 1]")
    print()
    print("🎯 数值含义:")
    print("   1.0  : 完全相同（向量方向完全一致）")
    print("   0.9+ : 非常相似（高度相关）")
    print("   0.7+ : 比较相似（相关性较强）")
    print("   0.5+ : 中等相似（有一定相关性）")
    print("   0.3+ : 低相似（相关性较弱）")
    print("   0.0  : 无关（向量正交）")
    print("   -0.3 : 负相关（方向相反）")
    print("   -1.0 : 完全相反（向量方向完全相反）")
    
    print("\n⚠️ 4. 实际应用中的特点")
    print("-" * 30)
    print("在文本嵌入中:")
    print("- 负值相似度较少见（文本很少完全相反）")
    print("- 大多数相似度在 [0, 1] 区间")
    print("- 高质量匹配通常 > 0.7")
    print("- 可接受匹配通常 > 0.3")

def demonstrate_similarity_calculation():
    """演示相似度计算过程"""
    print("\n🧪 5. 相似度计算演示")
    print("-" * 30)
    
    # 创建示例向量
    print("创建两个示例向量:")
    vec_a = np.array([1.0, 2.0, 3.0])
    vec_b = np.array([2.0, 4.0, 6.0])  # vec_a的2倍
    vec_c = np.array([1.0, 0.0, 0.0])  # 与vec_a部分相关
    vec_d = np.array([-1.0, -2.0, -3.0])  # vec_a的相反
    
    print(f"向量A: {vec_a}")
    print(f"向量B: {vec_b} (A的2倍)")
    print(f"向量C: {vec_c} (与A部分相关)")
    print(f"向量D: {vec_d} (A的相反)")
    
    def calculate_cosine_similarity(v1, v2):
        """计算余弦相似度"""
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        return dot_product / (norm_v1 * norm_v2)
    
    print("\n📊 相似度计算结果:")
    sim_ab = calculate_cosine_similarity(vec_a, vec_b)
    sim_ac = calculate_cosine_similarity(vec_a, vec_c)
    sim_ad = calculate_cosine_similarity(vec_a, vec_d)
    
    print(f"A与B的相似度: {sim_ab:.4f} (完全相同方向)")
    print(f"A与C的相似度: {sim_ac:.4f} (部分相关)")
    print(f"A与D的相似度: {sim_ad:.4f} (完全相反)")
    
    # 演示归一化后的内积
    print("\n🔄 归一化后的内积验证:")
    vec_a_norm = vec_a / np.linalg.norm(vec_a)
    vec_b_norm = vec_b / np.linalg.norm(vec_b)
    vec_c_norm = vec_c / np.linalg.norm(vec_c)
    
    inner_product_ab = np.dot(vec_a_norm, vec_b_norm)
    inner_product_ac = np.dot(vec_a_norm, vec_c_norm)
    
    print(f"归一化后A·B = {inner_product_ab:.4f} (等于余弦相似度)")
    print(f"归一化后A·C = {inner_product_ac:.4f} (等于余弦相似度)")

def analyze_faiss_index():
    """分析FAISS索引的配置"""
    print("\n🔧 6. FAISS索引配置分析")
    print("-" * 30)
    
    try:
        if os.path.exists("faiss_index.index"):
            index = faiss.read_index("faiss_index.index")
            print(f"✅ 索引类型: {type(index).__name__}")
            print(f"📏 向量维度: {index.d}")
            print(f"📊 向量数量: {index.ntotal}")
            
            if isinstance(index, faiss.IndexFlatIP):
                print("🎯 使用内积索引 (IndexFlatIP)")
                print("   - 配合向量归一化实现余弦相似度")
                print("   - 返回值即为余弦相似度")
            elif isinstance(index, faiss.IndexFlatL2):
                print("📐 使用L2距离索引 (IndexFlatL2)")
                print("   - 返回值为欧几里得距离的平方")
                print("   - 需要转换为相似度")
            
        else:
            print("⚠️ 未找到FAISS索引文件")
            
    except Exception as e:
        print(f"❌ 分析索引时出错: {e}")

def test_real_similarity():
    """测试真实文档的相似度"""
    print("\n🔍 7. 真实文档相似度测试")
    print("-" * 30)
    
    try:
        searcher = DocumentSearcher()
        
        # 测试查询
        test_queries = [
            "机器学习算法",
            "深度学习神经网络", 
            "数据挖掘技术",
            "完全不相关的内容xyz123"
        ]
        
        for query in test_queries:
            print(f"\n🔎 查询: '{query}'")
            results = searcher.search_similar_documents(query, top_k=3)
            
            if results:
                print("   前3个相似结果:")
                for i, result in enumerate(results[:3], 1):
                    score = result['similarity_score']
                    title = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
                    
                    # 相似度等级判断
                    if score >= 0.8:
                        level = "🔥 极高"
                    elif score >= 0.6:
                        level = "🟢 较高"
                    elif score >= 0.4:
                        level = "🟡 中等"
                    elif score >= 0.2:
                        level = "🟠 较低"
                    else:
                        level = "🔴 很低"
                    
                    print(f"   {i}. 相似度: {score:.4f} {level}")
                    print(f"      标题: {title}")
            else:
                print("   未找到相关结果")
        
        searcher.close()
        
    except Exception as e:
        print(f"❌ 测试时出错: {e}")

def similarity_threshold_guide():
    """相似度阈值使用指南"""
    print("\n📋 8. 相似度阈值使用指南")
    print("-" * 30)
    
    thresholds = [
        (0.9, "严格匹配", "只返回高度相关的结果，适用于精确查找"),
        (0.7, "高质量匹配", "返回相关性较强的结果，推荐用于一般检索"),
        (0.5, "中等匹配", "返回中等相关的结果，适用于探索性查找"),
        (0.3, "宽松匹配", "返回可能相关的结果，适用于广泛搜索"),
        (0.1, "极宽松匹配", "返回任何可能的结果，可能包含噪音")
    ]
    
    print("🎯 推荐阈值设置:")
    for threshold, name, description in thresholds:
        print(f"   {threshold:.1f}+ : {name}")
        print(f"         {description}")
        print()
    
    print("💡 实际应用建议:")
    print("- RAG系统: 建议使用 0.3-0.7 作为阈值")
    print("- 问答系统: 建议使用 0.5-0.8 作为阈值")
    print("- 文档推荐: 建议使用 0.2-0.5 作为阈值")
    print("- 可以根据实际效果动态调整阈值")

def main():
    """主函数"""
    print("📚 检索相似度计算详解")
    print("=" * 60)
    
    explain_similarity_calculation()
    demonstrate_similarity_calculation()
    analyze_faiss_index()
    test_real_similarity()
    similarity_threshold_guide()
    
    print("\n" + "=" * 60)
    print("📖 总结:")
    print("- 系统使用余弦相似度，取值范围 [-1, 1]")
    print("- 通过向量归一化 + 内积实现高效计算")
    print("- 相似度 > 0.7 表示高度相关")
    print("- 相似度 > 0.3 表示有一定相关性")
    print("- 可根据应用场景调整相似度阈值")

if __name__ == "__main__":
    main()
