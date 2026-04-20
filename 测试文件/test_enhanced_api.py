"""
测试增强后的API服务器功能
"""

import requests
import json
import time

# API服务器地址
BASE_URL = "http://localhost:8005"

def test_complexity_analyze():
    """测试复杂度分析API"""
    print("=== 测试复杂度分析API ===")

    test_queries = [
        "你好",
        "什么是机器学习？",
        "请比较深度学习和传统机器学习的优缺点",
        "分析量子计算在密码学中的应用前景"
    ]

    for query in test_queries:
        try:
            response = requests.post(
                f"{BASE_URL}/complexity/analyze",
                json={"query": query},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"查询: {query}")
                print(f"  复杂度评分: {result['complexity_analysis']['total_complexity']:.3f}")
                print(f"  复杂度等级: {result['complexity_analysis']['complexity_level']}")
                print("  ✅ 分析成功")
            else:
                print(f"❌ 分析失败: {response.status_code}")
                print(f"错误信息: {response.text}")

        except Exception as e:
            print(f"❌ 请求失败: {e}")

        print("-" * 50)

def test_routing_recommendation():
    """测试路由推荐API"""
    print("\n=== 测试路由推荐API ===")

    query = "分析比较深度学习中的CNN和RNN架构"

    try:
        response = requests.post(
            f"{BASE_URL}/complexity/route",
            json={"query": query},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"查询: {query}")
            print(f"推荐路由: {result['routing_result']['route']}")
            print(f"置信度: {result['routing_result']['confidence']:.3f}")
            print(f"网络状态: {result['network_status']}")
            print("  ✅ 推荐成功")
        else:
            print(f"❌ 推荐失败: {response.status_code}")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_complexity_routing():
    """测试复杂度路由API"""
    print("\n=== 测试复杂度路由API ===")

    test_cases = [
        {"query": "你好"},
        {"query": "什么是人工智能？"},
        {"query": "分析比较深度学习和传统机器学习的优缺点"},
        {"query": "结合量子计算分析未来AI发展趋势"}
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['query']}")

        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/complexity/route",
                json=case,
                timeout=30
            )
            end_time = time.time()

            if response.status_code == 200:
                result = response.json()
                routing_result = result['routing_result']
                complexity = routing_result['complexity_analysis']

                print(f"复杂度评分: {complexity['total_complexity']:.3f}")
                print(f"复杂度等级: {complexity['complexity_level']}")
                print(f"推荐路由: {routing_result['route']}")
                print(f"置信度: {routing_result['confidence']:.3f}")
                print(f"网络状态: {result['network_status']['cloud_available']}")
                print(f"处理时间: {end_time - start_time:.2f}秒")
                print("  ✅ 路由分析成功")
            else:
                print(f"❌ 路由分析失败: {response.status_code}")
                print(f"错误信息: {response.text}")

        except Exception as e:
            print(f"❌ 请求失败: {e}")

        print("-" * 50)

def test_system_status():
    """测试系统状态API"""
    print("\n=== 测试系统状态API ===")

    try:
        response = requests.get(f"{BASE_URL}/system/status", timeout=10)

        if response.status_code == 200:
            result = response.json()
            system_status = result['system_status']

            print("系统状态:")
            print(f"  时间戳: {system_status['timestamp']}")
            print(f"  网络状态: {system_status['network']['cloud_available']}")
            print(f"  当前模型: {system_status['current_model']}")
            print(f"  复杂度分析器查询数: {system_status['complexity_analyzer']['total_queries']}")
            print(f"  知识库文档数: {system_status['knowledge_base']['total_documents']}")
            print(f"  知识库块数: {system_status['knowledge_base']['total_chunks']}")
            print("  ✅ 状态获取成功")
        else:
            print(f"❌ 状态获取失败: {response.status_code}")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_feedback_collection():
    """测试反馈收集API"""
    print("\n=== 测试反馈收集API ===")

    try:
        response = requests.post(
            f"{BASE_URL}/feedback",
            json={
                "query": "什么是机器学习？",
                "route": "local_sufficient",
                "user_satisfaction": 0.8,
                "response_time": 1500
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"反馈结果: {result['message']}")
            print("  ✅ 反馈收集成功")
        else:
            print(f"❌ 反馈收集失败: {response.status_code}")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """运行所有测试"""
    print("开始测试增强后的API服务器...")
    print("=" * 60)

    # 检查API服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/system/status", timeout=5)
        if response.status_code != 200:
            print("❌ API服务器未运行或响应异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {e}")
        print("请确保API服务器在 http://localhost:8005 运行")
        return

    print("✅ API服务器连接正常")
    print("=" * 60)

    # 运行测试
    test_complexity_analyze()
    test_routing_recommendation()
    test_complexity_routing()
    test_system_status()
    test_feedback_collection()

    print("\n" + "=" * 60)
    print("所有测试完成！")

if __name__ == "__main__":
    main()