#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速隐私检测测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:8005"


def quick_test():
    """快速测试隐私检测功能"""
    print("🔍 快速隐私检测测试")

    # 测试数据
    test_cases = [
        {"query": "身份证号码是多少", "expected": "高风险"},
        {"query": "今天天气怎么样", "expected": "低风险"},
        {"query": "银行卡信息", "expected": "高风险"},
        {"query": "你好", "expected": "低风险"}
    ]

    for test in test_cases:
        print(f"\n📝 测试: '{test['query']}'")

        try:
            response = requests.post(
                f"{BASE_URL}/privacy_check",
                json={
                    "chat_history": [{"role": "user", "content": test['query']}],
                    "get_details": False
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                score = result.get("privacy_score", 0)
                is_risk = result.get("is_privacy_risk", False)

                status = "🔴 高风险" if is_risk else "🟢 低风险"
                expected_status = "🔴 高风险" if test['expected'] == "高风险" else "🟢 低风险"

                print(f"  分值: {score:.3f}")
                print(f"  结果: {status}")
                print(f"  期望: {expected_status}")
                print(result)
                print(f"  {'✅ 通过' if status == expected_status else '❌ 失败'}")

            else:
                print(f"  ❌ 请求失败: HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ 异常: {e}")


if __name__ == "__main__":
    quick_test()