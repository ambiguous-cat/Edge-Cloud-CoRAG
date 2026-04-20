"""
复杂度分析器测试用例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from complexity_analyzer import ComplexityAnalyzer
import json

def test_basic_complexity_analysis():
    """基础复杂度分析测试"""
    print("=== 基础复杂度分析测试 ===")

    analyzer = ComplexityAnalyzer()

    # 测试用例：不同复杂度的查询
    test_queries = [
        ("你好", "very_low"),
        ("什么是机器学习", "low"),
        ("请比较深度学习和机器学习的区别，并分析它们在不同应用场景下的优缺点", "high"),
        ("在量子计算和区块链技术的结合中，如何利用量子纠缠原理来优化分布式账本的共识机制，同时保证数据隐私和系统安全性？", "very_high")
    ]

    for query, expected_level in test_queries:
        result = analyzer.analyze_complexity(query)
        actual_level = result['complexity_level']
        total_score = result['total_complexity']

        print(f"查询: {query[:50]}...")
        print(f"  预期复杂度: {expected_level}")
        print(f"  实际复杂度: {actual_level} (评分: {total_score:.3f})")
        print(f"  详细评分: {json.dumps({k: v for k, v in result.items() if k != 'complexity_level'}, indent=2, ensure_ascii=False)}")
        print()

        # 简单验证
        level_order = ['very_low', 'low', 'medium', 'high', 'very_high']
        expected_idx = level_order.index(expected_level)
        actual_idx = level_order.index(actual_level)

        if abs(actual_idx - expected_idx) <= 1:  # 允许一个级别的误差
            print("[PASS] 测试通过")
        else:
            print("[FAIL] 测试失败 - 复杂度评估偏差较大")
        print("-" * 50)

def test_routing_decision():
    """路由决策测试"""
    print("\n=== 路由决策测试 ===")

    analyzer = ComplexityAnalyzer()

    # 模拟网络状态
    network_conditions = [
        None,  # 无网络信息
        {"cloud_available": True, "latency": 50, "bandwidth": 100},   # 网络良好
        {"cloud_available": True, "latency": 800, "bandwidth": 5},   # 网络较差
        {"cloud_available": False, "latency": 0, "bandwidth": 0}     # 云端不可用
    ]

    test_queries = [
        "什么是Python？",
        "请实现一个基于Transformer的文本分类模型，包括数据预处理、模型训练和评估的完整流程",
        "分析比较深度学习中CNN、RNN和Transformer三种架构在自然语言处理任务中的性能表现"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("=" * 80)

        for i, network in enumerate(network_conditions):
            network_name = ["无网络信息", "网络良好", "网络较差", "云端不可用"][i]
            print(f"\n网络状况: {network_name}")

            result = analyzer.route_based_on_complexity(query, network)

            print(f"  最终路由: {result['route']}")
            print(f"  基础路由: {result['base_route']}")
            print(f"  置信度: {result['confidence']:.3f}")
            print(f"  路由解释: {result['explanation']}")
            print(f"  建议: {', '.join(result['recommendations'])}")

def test_domain_specificity():
    """领域特定性测试"""
    print("\n=== 领域特定性测试 ===")

    analyzer = ComplexityAnalyzer()

    domain_queries = [
        ("编程和算法相关", "如何用Python实现快速排序算法，并分析其时间复杂度和空间复杂度？"),
        ("医学专业", "CRISPR-Cas9基因编辑技术在治疗遗传性疾病中的应用前景和伦理挑战是什么？"),
        ("金融经济", "在量化交易中，如何结合机器学习和统计分析来优化投资组合的风险收益比？"),
        "跨学科领域：结合量子物理学和计算机科学，分析量子算法在密码学中的应用潜力及对未来信息安全体系的影响"
    ]

    for item in domain_queries:
        if isinstance(item, tuple):
            description, query = item
        else:
            description = None
            query = item
        if description:
            print(f"\n{description}:")
            print(f"查询: {query}")
        else:
            print(f"\n{query}")

        result = analyzer.analyze_complexity(query)
        domain_score = result['domain_specificity']

        print(f"  领域特定性评分: {domain_score:.3f}")

        # 分析涉及的领域
        words = query.lower().split()
        involved_domains = []
        for domain, terms in analyzer.domain_terms.items():
            if any(term in query for term in terms):
                involved_domains.append(domain)

        if involved_domains:
            print(f"  涉及领域: {', '.join(involved_domains)}")
        else:
            print(f"  未检测到特定专业领域")

        print("-" * 40)

def test_reasoning_complexity():
    """推理复杂度测试"""
    print("\n=== 推理复杂度测试 ===")

    analyzer = ComplexityAnalyzer()

    reasoning_queries = [
        ("简单事实查询", "北京是中国的首都吗？"),
        ("比较分析", "比较Python和Java在Web开发方面的优缺点"),
        ("因果关系", "分析全球变暖对极端天气事件增加的具体影响机制"),
        ("多重推理", "如果云计算技术继续发展，那么不仅会改变传统的IT架构，而且还会对企业的数字化转型产生深远影响，请分析这种变化可能带来的机遇和挑战"),
        ("复杂条件推理", "当且仅当机器学习模型在训练集上表现良好，同时在测试集上也具有相似的泛化能力时，我们才能认为该模型是有效的，请分析这种判断标准在实际应用中的局限性")
    ]

    for description, query in reasoning_queries:
        print(f"\n{description}:")
        print(f"查询: {query}")

        result = analyzer.analyze_complexity(query)
        reasoning_score = result['reasoning_requirements']

        print(f"  推理需求评分: {reasoning_score:.3f}")

        # 分析涉及的推理模式
        query_lower = query.lower()
        involved_patterns = []
        for pattern, keywords in analyzer.reasoning_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                involved_patterns.append(pattern)

        if involved_patterns:
            print(f"  涉及推理模式: {', '.join(involved_patterns)}")

        print("-" * 60)

def test_feedback_learning():
    """反馈学习测试"""
    print("\n=== 反馈学习测试 ===")

    analyzer = ComplexityAnalyzer()

    # 模拟一些查询和反馈
    test_data = [
        ("简单查询", "你好", 0.9, 500),
        ("复杂查询", "分析机器学习在医疗诊断中的应用前景", 0.6, 2000),
        ("极复杂查询", "结合量子计算和区块链技术，设计一个去中心化的量子安全通信协议", 0.3, 5000)
    ]

    print("初始复杂度权重:")
    print(json.dumps(analyzer.complexity_weights, indent=2, ensure_ascii=False))

    # 提交反馈
    for description, query, satisfaction, response_time in test_data:
        route_result = analyzer.route_based_on_complexity(query)
        route = route_result['route']

        print(f"\n{description}:")
        print(f"  查询: {query}")
        print(f"  路由: {route}")
        print(f"  用户满意度: {satisfaction}")
        print(f"  响应时间: {response_time}ms")

        analyzer.learn_from_feedback(query, route, satisfaction, response_time)

        print("  反馈已记录")

    print(f"\n学习后的复杂度权重:")
    print(json.dumps(analyzer.complexity_weights, indent=2, ensure_ascii=False))

    # 获取统计信息
    stats = analyzer.get_complexity_statistics()
    print(f"\n统计信息:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

def test_edge_cases():
    """边界情况测试"""
    print("\n=== 边界情况测试 ===")

    analyzer = ComplexityAnalyzer()

    edge_cases = [
        ("空字符串", ""),
        ("非常长的查询", "请" * 100 + "详细分析" * 50 + "这个问题" * 30),
        ("只有标点符号", "！@#￥%……&*（）——+"),
        ("混合语言", "Hello 世界，what is 机器 learning and how does it work in 中文？"),
        ("只有数字", "1234567890 2024年3月15日 3.14159"),
        ("特殊字符", "机器人搜索电脑闪电数据灯泡目标火箭星星")
    ]

    for description, query in edge_cases:
        print(f"\n{description}:")
        print(f"输入: {repr(query)}")

        try:
            result = analyzer.analyze_complexity(query)
            print(f"  复杂度评分: {result['total_complexity']:.3f}")
            print(f"  复杂度等级: {result['complexity_level']}")
            print("[PASS] 处理成功")
        except Exception as e:
            print(f"[FAIL] 处理失败: {e}")

        print("-" * 40)

def main():
    """运行所有测试"""
    print("复杂度分析器测试开始")
    print("=" * 80)

    try:
        test_basic_complexity_analysis()
        test_routing_decision()
        test_domain_specificity()
        test_reasoning_complexity()
        test_feedback_learning()
        test_edge_cases()

        print("\n" + "=" * 80)
        print("所有测试完成！")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()