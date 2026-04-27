import time
from typing import Dict, Generator, List, Optional

from chat_model import API_KEY, CHAT_URL, chat as proxy_chat, simple_chat, stream_chat as proxy_stream_chat


def chat(messages: List[Dict[str, str]], model: str = "glm-4.6", api_key: Optional[str] = None, **kwargs) -> str:
    if api_key is not None:
        kwargs["api_key"] = api_key
    return proxy_chat(messages, model=model, **kwargs)


def chat_stream_chat(
    messages: List[Dict[str, str]], model: str = "glm-4.6", api_key: Optional[str] = None, **kwargs
) -> Generator[str, None, None]:
    if api_key is not None:
        kwargs["api_key"] = api_key
    return proxy_stream_chat(messages, model=model, **kwargs)


def test_chat_model():
    test_message = "你好，请简单介绍一下你自己。"
    print("=== 对话模型测试 ===")
    print(f"聊天地址: {CHAT_URL}")

    if not API_KEY:
        print("未找到 API key，请在 .env 中配置")
        return False

    try:
        print("正在生成回复...")
        start_time = time.time()
        response = simple_chat(test_message)
        end_time = time.time()

        print(f"回复成功，耗时: {end_time - start_time:.2f}s")
        print(f"回复: {response}")
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


if __name__ == "__main__":
    test_chat_model()
