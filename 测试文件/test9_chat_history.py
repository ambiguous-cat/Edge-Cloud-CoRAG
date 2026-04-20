#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
import json

API_BASE = "http://localhost:8005"


def check_api_status():
    """检查API服务是否运行"""
    try:
        response = requests.get(f"{API_BASE}/docs", timeout=5)
        return response.status_code == 200
    except:
        return False


def simple_chat(message, history=None):
    """简单对话测试"""
    print(f"🗣️ 用户: {message}")

    data = {
        "message": message,
        "model_type": "gpt-4",
        "stream": True,
        "history": history or []
    }

    try:
        response = requests.post(f"{API_BASE}/chat", json=data, stream=True, timeout=60)
        if response.status_code == 200:
            print("🤖 助手: ", end="", flush=True)
            full_reply = ""

            try:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            try:
                                chunk_data = json.loads(data_str)
                                if not chunk_data.get('done', False):
                                    content = chunk_data.get('content', '')
                                    print(content, end="", flush=True)
                                    full_reply += content
                                else:
                                    if 'error' in chunk_data:
                                        print(f"\n❌ 流式错误: {chunk_data['error']}")
                                        return None
                                    else:
                                        print()  # 换行
                                        return full_reply
                            except json.JSONDecodeError:
                                continue

                # 如果没有收到done信号，返回已收集的内容
                print()  # 换行
                return full_reply if full_reply else None

            except Exception as stream_err:
                print(f"\n❌ 流式处理错误: {stream_err}")
                return None
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}...")
            return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def test_multi_turn_chat():
    """测试多轮对话"""
    print("\n📝 测试多轮对话")
    print("-" * 40)

    history = []

    # 第一轮
    reply1 = simple_chat("你好，我想学Python")
    if reply1:
        history.extend([
            {"role": "user", "content": "你好，我想学Python"},
            {"role": "assistant", "content": reply1}
        ])

    # 第二轮（带历史）
    if history:
        print(f"\n(历史记录: {len(history)}条)")
        reply2 = simple_chat("从哪里开始学？", history)
        if reply2:
            history.extend([
                {"role": "user", "content": "从哪里开始学？"},
                {"role": "assistant", "content": reply2}
            ])




def main():
    """主函数"""
    print("🚀 简化版聊天测试")
    print("=" * 50)

    # 检查服务状态
    if not check_api_status():
        print("❌ API服务未运行，请先启动:")
        print("   python api_server.py")
        return

    print("✅ API服务运行正常")

    try:
        # 运行测试
        test_multi_turn_chat()


        print("\n" + "=" * 50)
        print("🎉 测试完成")

    except KeyboardInterrupt:
        print("\n❌ 测试被中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")


if __name__ == "__main__":
    main()
