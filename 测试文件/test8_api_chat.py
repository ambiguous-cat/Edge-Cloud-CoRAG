#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API对话接口测试文件
测试普通对话和RAG对话接口
"""

import requests
import json
import time

API_BASE = "http://localhost:8005"

def test_simple_chat():
    """测试普通对话接口"""
    print("🗣️ 测试普通对话接口")
    print("-" * 40)
    
    # 1. 普通对话（无文档）
    print("1. 普通对话（无文档）:")
    data = {
        "message": "你好，请简单介绍一下你自己",
        "model_type": "qwen3:1.7b",
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/chat", json=data, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功 ({elapsed:.2f}秒)")
            print(f"回答: {result['response'][:100]}...")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 2. 带文档的对话（流式）
    print("\n2. 带文档的对话（流式）:")
    
    # 模拟用户上传的文档
    uploaded_documents = [
        {
            "title": "Python编程指南",
            "content": "Python是一种高级编程语言，具有简洁的语法和强大的功能。它广泛应用于Web开发、数据科学、机器学习等领域。Python的特点包括：易学易用、跨平台、丰富的库生态等。",
            "similarity_score": 1.0,
            "source": "用户上传"
        },
        {
            "title": "机器学习基础",
            "content": "机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习和改进。常见的机器学习算法包括线性回归、决策树、神经网络等。",
            "similarity_score": 0.9,
            "source": "用户上传"
        }
    ]
    
    data = {
        "message": "Python在机器学习中有什么优势？",
        "model_type": "qwen3:1.7b",
        "stream": True,
        "documents": uploaded_documents
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/chat", json=data, stream=True, timeout=60)
        
        if response.status_code == 200:
            print("回答: ", end="", flush=True)
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        try:
                            chunk_data = json.loads(data_str)
                            if not chunk_data.get('done', False):
                                print(chunk_data.get('content', ''), end="", flush=True)
                            else:
                                if 'error' in chunk_data:
                                    print(f"\n❌ 流式错误: {chunk_data['error']}")
                                else:
                                    elapsed = time.time() - start_time
                                    print(f"\n✅ 流式完成 ({elapsed:.2f}秒)")
                                break
                        except json.JSONDecodeError:
                            continue
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 3. 空文档测试
    print("\n3. 空文档列表测试:")
    data = {
        "message": "请介绍一下深度学习",
        "model_type": "llama3.1",
        "stream": False,
        "documents": []  # 空文档列表
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/chat", json=data, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功 ({elapsed:.2f}秒)")
            print(f"回答: {result['response'][:100]}...")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_rag_chat():
    """测试RAG对话接口"""
    print("\n🤖 测试RAG对话接口")
    print("-" * 40)
    
    # 非流式RAG对话
    print("1. 非流式RAG对话:")
    data = {
        "query": "辰天是谁？",
        "model_type": "llama3.1",
        "top_k": 3,
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/rag_chat", json=data, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功 ({elapsed:.2f}秒)")
            print(f"回答: {result['response'][:100]}...")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 流式RAG对话
    print("\n2. 流式RAG对话:")
    data = {
        "query": "什么是武者之魂？",
        "model_type": "llama3.1",
        "top_k": 2,
        "stream": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/rag_chat", json=data, stream=True, timeout=60)
        
        if response.status_code == 200:
            print("回答: ", end="", flush=True)
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        try:
                            chunk_data = json.loads(data_str)
                            if not chunk_data.get('done', False):
                                print(chunk_data.get('content', ''), end="", flush=True)
                            else:
                                if 'error' in chunk_data:
                                    print(f"\n❌ 流式错误: {chunk_data['error']}")
                                else:
                                    elapsed = time.time() - start_time
                                    print(f"\n✅ 流式完成 ({elapsed:.2f}秒)")
                                break
                        except json.JSONDecodeError:
                            continue
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    """主测试函数"""
    print("🚀 API对话接口测试")
    print("=" * 50)

    
    try:
        # 2. 测试普通对话接口
        test_simple_chat()
        
        # 3. 测试RAG对话接口
        test_rag_chat()
        
        print("\n" + "=" * 50)
        print("🎉 API接口测试完成")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    main()
