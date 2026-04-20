#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试隐私检测器，绕过API层
"""

import sys
sys.path.append('..')
from privacy_detector import PrivacyDetector
import numpy as np

def test_privacy_directly():
    """直接测试隐私检测器"""
    print("=== 直接测试隐私检测器 ===\n")

    # 创建隐私检测器实例
    try:
        detector = PrivacyDetector()
        print(f"✅ 隐私检测器创建成功")
        print(f"隐私关键词数量: {len(detector.privacy_keywords)}")
        print(f"隐私问句数量: {len(detector.question_mapping)}")
        print(f"FAISS索引状态: {'已加载' if detector.faiss_index else '未加载'}")
        print(f"相似度阈值: {detector.similarity_threshold}")
    except Exception as e:
        print(f"❌ 隐私检测器创建失败: {e}")
        return

    # 测试用例
    test_cases = [
        ("我的身份证号码是多少", "应该检测到 - 隐私问句"),
        ("我的手机号码是多少", "应该检测到 - 隐私问句"),
        ("我的银行卡余额查询", "应该检测到 - 隐私问句"),
        ("请帮我重置密码", "应该检测到 - 隐私问句"),
        ("今天天气怎么样", "不应该检测到"),
        ("请介绍一下人工智能", "不应该检测到"),
        ("你好", "不应该检测到")
    ]

    print("\n=== 测试用例 ===")
    for i, (text, description) in enumerate(test_cases, 1):
        print(f"\n{i}. 测试: {text}")
        print(f"   期望: {description}")

        # 构建聊天历史
        chat_history = [{"role": "user", "content": text}]

        try:
            # 测试关键词检测
            keyword_detected = detector._check_keywords(text)
            print(f"   关键词检测: {'命中' if keyword_detected else '未命中'}")

            # 测试语义相似度检测
            semantic_score = detector._check_semantic_similarity(text)
            print(f"   语义相似度: {semantic_score:.3f}")

            # 测试完整隐私分数
            privacy_score = detector.detect_privacy_score(chat_history)
            print(f"   最终隐私分数: {privacy_score:.3f}")

            # 判断结果
            expected_high = "应该" in description
            actual_high = privacy_score >= detector.similarity_threshold

            if expected_high == actual_high:
                print(f"   结果: ✅ 通过")
            else:
                print(f"   结果: ❌ 失败 (期望: {'高' if expected_high else '低'}, 实际: {'高' if actual_high else '低'})")

        except Exception as e:
            print(f"   错误: {e}")

    print("\n=== 调试FAISS检索 ===")
    # 测试一个与隐私问句相似的问题
    test_query = "我的身份证信息"
    print(f"测试查询: {test_query}")

    try:
        if detector.faiss_index and detector.question_mapping:
            # 生成查询向量
            from embedding import get_embedding
            query_embedding = get_embedding(test_query)
            print(f"查询向量长度: {len(query_embedding) if query_embedding else 'None'}")
            print(f"查询向量类型: {type(query_embedding) if query_embedding else 'None'}")

            if query_embedding is not None:
                import faiss
                query_vec = np.array([query_embedding], dtype=np.float32)
                print(f"FAISS查询向量形状: {query_vec.shape}")

                # 执行检索
                similarities, indices = detector.faiss_index.search(query_vec, 3)  # 检索前3个最相似的
                print(f"FAISS检索结果:")
                print(f"  相似度: {similarities[0]}")
                print(f"  索引: {indices[0]}")

                if len(indices[0]) > 0 and indices[0][0] < len(detector.question_mapping):
                    matched_question = detector.question_mapping[indices[0][0]]
                    print(f"  匹配问句: {matched_question}")
                else:
                    print("  没有匹配的问句")
            else:
                print("查询向量生成为空")
        else:
            print("FAISS索引或问句映射未加载")
    except Exception as e:
        print(f"FAISS检索错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_privacy_directly()