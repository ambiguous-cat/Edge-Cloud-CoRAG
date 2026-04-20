#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话模型流式测试文件
测试 llama3.1 和 gpt-4 两个模型的流式响应功能
"""

import chat_model
import time
from typing import Generator

def test_model_stream(model_name: str, test_query: str):
    """
    测试指定模型的流式响应
    """
    print(f"\n[{model_name} 流式测试]")
    print(f"问题: {test_query}")
    
    # 切换到指定模型
    try:
        chat_model.set_chat_model(model_name)
        print(f"切换到模型: {model_name}")
    except Exception as e:
        print(f"切换模型失败: {e}")
        return False
    
    # 构建消息
    messages = [{"role": "user", "content": test_query}]
    
    print("流式响应:")
    
    start_time = time.time()
    total_tokens = 0
    
    try:
        # 流式对话测试
        response_text = ""
        for chunk in chat_model.stream_chat(messages, max_tokens=200, temperature=0.7):
            print(chunk, end='', flush=True)
            response_text += chunk
            total_tokens += len(chunk.split())
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n响应时间: {elapsed_time:.2f}秒, 总词数: {total_tokens}, 速度: {total_tokens/elapsed_time:.1f}词/秒")
        print(f"{model_name} 流式测试完成")
        
        return True
        
    except Exception as e:
        print(f"\n{model_name} 流式测试失败: {e}")
        return False

def test_non_stream_comparison(model_name: str, test_query: str):
    """
    对比测试：非流式响应
    """
    print(f"\n[{model_name} 非流式测试]")
    
    try:
        chat_model.set_chat_model(model_name)
        messages = [{"role": "user", "content": test_query}]
        
        start_time = time.time()
        response = chat_model.chat(messages, max_tokens=200, temperature=0.7)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        print(f"非流式响应时间: {elapsed_time:.2f}秒")
        print(f"完整回复: {response[:100]}...")
        print(f"{model_name} 非流式测试完成")
        
        return True
        
    except Exception as e:
        print(f"{model_name} 非流式测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("对话模型测试程序")
    
    # 测试问题
    test_question = "请简单详细一下你自己，包括你的能力和特点。"
    
    # 要测试的模型
    models_to_test = ['llama3.1', 'gpt-4']
    
    results = {}
    
    for model in models_to_test:
        try:
            # 流式测试
            success_stream = test_model_stream(model, test_question)
            results[f"{model}_stream"] = success_stream
            
            time.sleep(1)
            
            # 非流式对比测试
            success_normal = test_non_stream_comparison(model, test_question)
            results[f"{model}_normal"] = success_normal
            
            time.sleep(2)  # 测试间隔
            
        except KeyboardInterrupt:
            print(f"\n用户中断测试")
            return
        except Exception as e:
            print(f"\n测试 {model} 时发生错误: {e}")
            results[f"{model}_error"] = False
    
    # 打印测试总结
    print_test_summary(results)

def print_test_summary(results: dict):
    """打印测试总结"""
    print(f"\n测试结果总结:")
    
    # 详细结果
    for test_name, success in results.items():
        status = "成功" if success else "失败"
        print(f"  {test_name}: {status}")
    
    print("测试完成")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n测试被用户中断")
    except Exception as e:
        print(f"\n测试程序出错: {e}")
    finally:
        print(f"\n程序结束")
