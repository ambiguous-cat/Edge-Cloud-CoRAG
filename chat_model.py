import os
import time
import requests
import openai
from dotenv import load_dotenv
from typing import List, Dict, Any, Generator, Optional

load_dotenv()  # 加载.env文件

# 读取配置
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip('/')  # 去除末尾斜杠


# 可用的对话模型
chat_models = ['qwen3:1.7b']
chat_model = chat_models[0]


def chat(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    统一的对话接口
    messages: [{"role": "user", "content": "..."}]
    """
    if chat_model not in chat_models:
        raise ValueError(f"不支持的模型: {chat_model}")
    elif chat_model == 'qwen3:1.7b':
        return qwen_chat(messages, "qwen3:1.7b", **kwargs)


def stream_chat(messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
    """
    流式对话接口
    """
    if chat_model not in chat_models:
        raise ValueError(f"不支持的模型: {chat_model}")
    elif chat_model == 'qwen3:1.7b':
        return qwen_stream_chat(messages, "qwen3:1.7b", **kwargs)



# Qwen 模型封装（通过Ollama）
def qwen_chat(messages: List[Dict[str, str]], model: str, **kwargs) -> str:
    """
    调用本地 Ollama 的对话模型
    """
    url = f"{OLLAMA_HOST}/api/chat"

    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": kwargs.get('temperature', 0.1),  # 降低到0.1以提高速度
            "num_predict": kwargs.get('max_tokens', 1000),
        }
    }

    try:
        # 增加超时时间并添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=data, timeout=30)  # 设置为30秒
                response.raise_for_status()
                result = response.json()
                return result["message"]["content"]
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"⚠️ 请求超时，正在重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    raise
            except requests.exceptions.ConnectionError:
                print("❌ 无法连接到Ollama服务，请检查服务是否运行")
                print("   可以运行: ollama serve")
                raise
    except Exception as e:
        print(f"Ollama对话出错: {e}")
        raise

def qwen_stream_chat(messages: List[Dict[str, str]], model: str, **kwargs) -> Generator[
    str, None, None]:
    """
    Qwen 流式对话
    """
    url = f"{OLLAMA_HOST}/api/chat"

    data = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": kwargs.get('temperature', 0.1),  # 降低到0.1以提高速度
            "num_predict": kwargs.get('max_tokens', 1000),
        }
    }

    try:
        response = requests.post(url, json=data, stream=True, timeout=30)  # 设置为30秒
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                import json
                chunk = json.loads(line)
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
                if chunk.get("done", False):
                    break
    except requests.exceptions.Timeout:
        print("❌ Ollama流式对话超时")
        print("   建议: 使用更小的模型或减少输出长度")
        raise
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Ollama服务")
        print("   请检查Ollama服务是否运行: ollama serve")
        raise
    except requests.exceptions.HTTPError as e:
        print(f"❌ Ollama HTTP错误: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            try:
                print(f"响应内容: {e.response.text[:200]}...")
            except:
                pass
        raise
    except Exception as e:
        print(f"Ollama流式对话出错: {e}")
        raise



# 工具函数
def set_chat_model(model_name: str):
    """设置当前使用的对话模型"""
    global chat_model
    if model_name in chat_models:
        chat_model = model_name
        print(f"对话模型已切换为: {model_name}")
    else:
        raise ValueError(f"不支持的模型: {model_name}，可用模型: {chat_models}")


def get_current_model() -> str:
    """获取当前使用的对话模型"""
    return chat_model


def get_available_models() -> List[str]:
    """获取所有可用的对话模型"""
    return chat_models.copy()


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
    print(f"当前模型: {get_current_model()}")
    print(f"Ollama地址: {OLLAMA_HOST}")
    print(f"测试消息: {test_message}")

    # 首先测试连接
    print("\n1. 测试Ollama连接...")
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        if response.status_code == 200:
            print("✅ Ollama服务连接正常")
            models = response.json().get("models", [])
            if models:
                print(f"   可用模型: {[m['name'] for m in models]}")
            else:
                print("⚠️ 没有找到可用模型")
        else:
            print(f"❌ Ollama服务响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到Ollama服务: {e}")
        print("   请检查Ollama是否运行: ollama serve")
        return False

    # 然后测试对话
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
