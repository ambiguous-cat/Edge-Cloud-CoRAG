

import os
import time
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any, Generator, Optional

load_dotenv()  # 加载.env文件

# 读取配置
ZHIPU_API_KEY = "58059201c0024f54a15245fd1d8cea84.JPY4o6pW9ixuhVbY"

# 可用的对话模型




# 智谱AI对话模型封装
def chat(messages: List[Dict[str, str]], model: str = "glm-4.6",
               api_key: Optional[str] = None, **kwargs) -> str:
    """
    调用智谱AI的对话模型
    """


    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": kwargs.get('temperature', 0.7),
        "max_tokens": kwargs.get('max_tokens', 1000),
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API响应格式异常: {result}")

    except requests.exceptions.RequestException as e:
        print(f"智谱AI API请求出错: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"错误详情: {error_detail}")
            except:
                print(f"响应内容: {e.response.text[:200]}...")
        raise
    except Exception as e:
        print(f"智谱AI对话出错: {e}")
        raise


def chat_stream_chat(messages: List[Dict[str, str]], model: str = "glm-4.6",
                      api_key: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
    """
    智谱AI流式对话
    """
    if api_key is None:
        api_key = ZHIPU_API_KEY
    if not api_key:
        raise ValueError("智谱API密钥未设置，请设置ZHIPU_API_KEY环境变量")

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": kwargs.get('temperature', 0.7),
        "max_tokens": kwargs.get('max_tokens', 1000),
        "stream": True
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]  # 去掉"data: "前缀
                    if data_str == '[DONE]':
                        break

                    try:
                        chunk = json.loads(data_str)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    except requests.exceptions.RequestException as e:
        print(f"智谱AI流式API请求出错: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"错误详情: {error_detail}")
            except:
                print(f"响应内容: {e.response.text[:200]}...")
        raise
    except Exception as e:
        print(f"智谱AI流式对话出错: {e}")
        raise




def simple_chat(message: str, **kwargs) -> str:
    """
    简单对话接口，自动构建消息格式
    """
    messages = [{"role": "user", "content": message}]
    return chat(messages, **kwargs)


# 测试函数
def test_chat_model():
    """测试对话模型功能"""
    test_message = "你好，请简单介绍一下你自己。"

    print("=== 对话模型测试 ===")
    print(f"使用智谱AI API")
    print(f"测试消息: {test_message}")

    # 检查智谱API配置
    print("\n1. 检查智谱API配置...")
    if not ZHIPU_API_KEY:
        print("❌ 未找到智谱API密钥，请设置ZHIPU_API_KEY环境变量")
        return False
    else:
        print("✅ 智谱API密钥配置正常")

    # 测试对话
    print("\n2. 测试模型对话...")
    try:
        print("⏳ 正在生成回复...")
        start_time = time.time()
        response = simple_chat(test_message)
        end_time = time.time()

        print(f"✅ 回复成功 (耗时: {end_time - start_time:.2f}秒)")
        print(f"回复: {response}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 运行测试
    test_chat_model()