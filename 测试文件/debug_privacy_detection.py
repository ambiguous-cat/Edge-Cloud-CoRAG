#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隐私检测问题调试脚本
"""

import requests
import json

def test_privacy_detection():
    """测试不同类型问题的隐私检测"""

    base_url = "http://localhost:8005"

    test_cases = [
        {
            "name": "包含隐私关键词",
            "message": "我的身份证号码是多少",
            "expected_high": True
        },
        {
            "name": "包含手机号关键词",
            "message": "我的手机号码忘记了",
            "expected_high": True
        },
        {
            "name": "包含密码关键词",
            "message": "请帮我重置密码",
            "expected_high": True
        },
        {
            "name": "包含银行卡关键词",
            "message": "我的银行卡余额查询",
            "expected_high": True
        },
        {
            "name": "普通学术问题",
            "message": "请介绍一下机器学习的基本原理",
            "expected_high": False
        },
        {
            "name": "简单问候",
            "message": "你好",
            "expected_high": False
        },
        {
            "name": "文档检索问题",
            "message": "深度学习相关的论文有哪些",
            "expected_high": False
        }
    ]

    print("=== 隐私检测测试 ===\n")

    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        print(f"问题: {test_case['message']}")

        try:
            response = requests.post(
                f"{base_url}/privacy_check",
                json={
                    "chat_history": [{"role": "user", "content": test_case['message']}],
                    "get_details": True
                },
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                privacy_score = result.get("privacy_score", 0.0)
                is_risk = result.get("is_privacy_risk", False)
                details = result.get("details", {})

                print(f"隐私分数: {privacy_score:.3f}")
                print(f"隐私风险: {'是' if is_risk else '否'}")

                # 显示检测详情
                detection_details = details.get("detection_details", [])
                if detection_details:
                    detail = detection_details[0]
                    keyword_detected = detail.get("keyword_detected", False)
                    semantic_score = detail.get("semantic_score", 0.0)

                    print(f"关键词检测: {'命中' if keyword_detected else '未命中'}")
                    print(f"语义相似度: {semantic_score:.3f}")

                # 判断测试结果
                if test_case['expected_high']:
                    status = "✅ 通过" if privacy_score > 0.5 else "❌ 失败"
                else:
                    status = "✅ 通过" if privacy_score < 0.5 else "❌ 失败"

                print(f"测试结果: {status}")

            else:
                print(f"API调用失败: {response.status_code}")
                print(f"错误信息: {response.text}")

        except Exception as e:
            print(f"测试失败: {e}")

        print("-" * 50)

    print("\n=== 隐私关键词列表 ===")
    try:
        response = requests.get(f"{base_url}/privacy/keywords", timeout=5)
        if response.status_code == 200:
            keywords = response.json()
            if keywords:
                print(f"当前共有 {len(keywords)} 个隐私关键词:")
                for i, keyword in enumerate(keywords[:10], 1):  # 只显示前10个
                    print(f"  {i}. {keyword}")
                if len(keywords) > 10:
                    print(f"  ... 还有 {len(keywords) - 10} 个")
            else:
                print("❌ 没有找到隐私关键词")
        else:
            print(f"获取关键词失败: {response.status_code}")
    except Exception as e:
        print(f"获取关键词失败: {e}")

if __name__ == "__main__":
    test_privacy_detection()