import os
import time
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any, Generator, Optional

load_dotenv()  # 加载.env文件

# 读取配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

# 可用的对话模型
chat_models = ['glm-4']
chat_model = chat_models[0]  # 默认使用glm-4


def chat(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    统一的对话接口
    messages: [{"role": "user", "content": "..."}]
    """
    if chat_model not in chat_models:
        raise ValueError(f"不支持的模型: {chat_model}")
    elif chat_model == 'glm-4':
        return zhipu_chat(messages, **kwargs)


def stream_chat(messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
    """
    流式对话接口
    """
    if chat_model not in chat_models:
        raise ValueError(f"不支持的模型: {chat_model}")
    elif chat_model == 'glm-4':
        return zhipu_stream_chat(messages, **kwargs)


# 智谱AI对话模型封装
def zhipu_chat(messages: List[Dict[str, str]], model: str = "glm-4",
               api_key: Optional[str] = None, **kwargs) -> str:
    """
    调用智谱AI的对话模型
    """
    if api_key is None:
        api_key = ZHIPU_API_KEY
    if not api_key:
        raise ValueError("智谱API密钥未设置")

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": kwargs.get('temperature', 0.1),  # 降低默认温度
        "max_tokens": kwargs.get('max_tokens', 500),  # 减少默认token数
        "stream": False
    }

    # 添加详细的性能监控
    start_time = time.time()
    dns_time = connection_time = None

    try:
        # 使用更短的超时时间
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        total_time = time.time() - start_time
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            print(f"✅ 非流式响应成功 | 总耗时: {total_time:.2f}s | 响应长度: {len(content)}字符")
            return content
        else:
            raise Exception(f"API响应格式异常: {result}")

    except requests.exceptions.Timeout:
        total_time = time.time() - start_time
        print(f"❌ 请求超时: {total_time:.2f}秒")
        raise Exception(f"请求超时 ({total_time:.2f}秒)")
    except requests.exceptions.RequestException as e:
        total_time = time.time() - start_time
        print(f"❌ 请求异常 (耗时{total_time:.2f}s): {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"状态码: {e.response.status_code}")
        raise
    except Exception as e:
        total_time = time.time() - start_time
        print(f"❌ 处理异常 (耗时{total_time:.2f}s): {e}")
        raise


def zhipu_stream_chat(messages: List[Dict[str, str]], model: str = "glm-4",
                      api_key: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
    """
    智谱AI流式对话
    """
    if api_key is None:
        api_key = ZHIPU_API_KEY
    if not api_key:
        raise ValueError("智谱API密钥未设置")

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": kwargs.get('temperature', 0.1),
        "max_tokens": kwargs.get('max_tokens', 500),
        "stream": True
    }

    start_time = time.time()
    first_token_received = False
    first_token_time = None
    content_length = 0

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str.strip() == '[DONE]':
                        total_time = time.time() - start_time
                        print(
                            f"✅ 流式响应完成 | 首字: {first_token_time:.2f}s | 总耗时: {total_time:.2f}s | 总长度: {content_length}字符")
                        break

                    try:
                        chunk = json.loads(data_str)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                content = delta["content"]
                                content_length += len(content)

                                # 记录首字时间
                                if not first_token_received:
                                    first_token_received = True
                                    first_token_time = time.time() - start_time
                                    print(f"🚀 收到首字: {first_token_time:.2f}s")

                                yield content
                    except json.JSONDecodeError:
                        continue

    except requests.exceptions.Timeout:
        total_time = time.time() - start_time
        print(f"❌ 流式请求超时: {total_time:.2f}秒")
        raise
    except Exception as e:
        total_time = time.time() - start_time
        print(f"❌ 流式处理异常 (耗时{total_time:.2f}s): {e}")
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
        response = simple_chat(test_message,)
        end_time = time.time()

        print(f"✅ 回复成功 (耗时: {end_time - start_time:.2f}秒)")
        print(f"回复: {response}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_performance():
    """性能测试函数"""
    test_message = "你好，请用100字左右简单介绍一下你自己。"

    print("=== 性能测试开始 ===\n")

    # 测试非流式
    print("1. 测试非流式响应:")
    try:
        response = simple_chat(test_message, model="glm-4")  # 明确指定模型
        print(f"回复: {response[:100]}...\n")
    except Exception as e:
        print(f"非流式测试失败: {e}\n")

    # 测试流式
    print("2. 测试流式响应:")
    try:
        messages = [{"role": "user", "content": test_message}]
        full_response = ""
        for chunk in stream_chat(messages, model="glm-4"):
            full_response += chunk
            print(chunk, end="", flush=True)
        print(f"\n完整回复长度: {len(full_response)}字符\n")
    except Exception as e:
        print(f"流式测试失败: {e}\n")

if __name__ == "__main__":
    # 运行测试
    test_performance()
    test_chat_model()