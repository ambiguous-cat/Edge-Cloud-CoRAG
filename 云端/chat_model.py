import json
import os
import time
from typing import Dict, Generator, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Chat config: keep it simple, one URL + one key.
CHAT_URL = os.getenv("CHAT_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
CHAT_API_KEY = os.getenv("CHAT_API_KEY", "")

# Compatibility export for old imports.
API_KEY = CHAT_API_KEY

DEFAULT_MODEL = os.getenv("CHAT_MODEL", "glm-4")
CHAT_MODELS = [m.strip() for m in os.getenv("CHAT_MODELS", DEFAULT_MODEL).split(",") if m.strip()]
DEFAULT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "0.1"))
DEFAULT_MAX_TOKENS = int(os.getenv("CHAT_MAX_TOKENS", "500"))
DEFAULT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT", "30"))

chat_models = CHAT_MODELS or [DEFAULT_MODEL]
chat_model = chat_models[0]


def chat(messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> str:
    return call_chat_completion(messages, model=model or chat_model, **kwargs)


def stream_chat(messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
    return stream_chat_completion(messages, model=model or chat_model, **kwargs)


def call_chat_completion(
    messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, api_key: Optional[str] = None, **kwargs
) -> str:
    if api_key is None:
        api_key = CHAT_API_KEY
    if not api_key:
        raise ValueError("Chat API key is missing, set CHAT_API_KEY in .env")

    timeout = int(kwargs.pop("timeout", DEFAULT_TIMEOUT))
    payload = {
        "model": model,
        "messages": messages,
        "temperature": kwargs.pop("temperature", DEFAULT_TEMPERATURE),
        "max_tokens": kwargs.pop("max_tokens", DEFAULT_MAX_TOKENS),
        "stream": False,
    }
    payload.update(kwargs)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    start_time = time.time()
    response = requests.post(CHAT_URL, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()

    if "choices" not in result or not result["choices"]:
        raise ValueError(f"Unexpected API response format: {result}")

    content = result["choices"][0]["message"]["content"]
    print(f"chat ok | elapsed: {time.time() - start_time:.2f}s | chars: {len(content)}")
    return content


def stream_chat_completion(
    messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, api_key: Optional[str] = None, **kwargs
) -> Generator[str, None, None]:
    if api_key is None:
        api_key = CHAT_API_KEY
    if not api_key:
        raise ValueError("Chat API key is missing, set CHAT_API_KEY in .env")

    timeout = int(kwargs.pop("timeout", DEFAULT_TIMEOUT))
    payload = {
        "model": model,
        "messages": messages,
        "temperature": kwargs.pop("temperature", DEFAULT_TEMPERATURE),
        "max_tokens": kwargs.pop("max_tokens", DEFAULT_MAX_TOKENS),
        "stream": True,
    }
    payload.update(kwargs)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    start_time = time.time()
    first_token_time = None
    content_length = 0

    with requests.post(CHAT_URL, headers=headers, json=payload, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if not line_str.startswith("data: "):
                continue

            data_str = line_str[6:]
            if data_str.strip() == "[DONE]":
                total_time = time.time() - start_time
                first_token_display = first_token_time if first_token_time is not None else total_time
                print(
                    f"stream done | first token: {first_token_display:.2f}s | elapsed: {total_time:.2f}s | chars: {content_length}"
                )
                break

            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if "choices" not in chunk or not chunk["choices"]:
                continue

            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content")
            if not content:
                continue

            if first_token_time is None:
                first_token_time = time.time() - start_time
                print(f"first token in {first_token_time:.2f}s")

            content_length += len(content)
            yield content


def set_chat_model(model_name: str):
    global chat_model
    if not model_name or not model_name.strip():
        raise ValueError("model_name cannot be empty")
    chat_model = model_name.strip()
    if chat_model not in chat_models:
        chat_models.append(chat_model)
    print(f"chat model switched to: {chat_model}")


def get_current_model() -> str:
    return chat_model


def get_available_models() -> List[str]:
    return chat_models.copy()


def simple_chat(message: str, **kwargs) -> str:
    return chat([{"role": "user", "content": message}], **kwargs)


def test_chat_model():
    print("=== Chat Model Test ===")
    print(f"current model: {get_current_model()}")
    print(f"chat url: {CHAT_URL}")
    if not CHAT_API_KEY:
        print("CHAT_API_KEY missing, check .env")
        return False
    try:
        start = time.time()
        resp = simple_chat("Hello, introduce yourself in one sentence.")
        print(f"success, elapsed: {time.time() - start:.2f}s")
        print(resp)
        return True
    except Exception as exc:
        print(f"test failed: {exc}")
        return False


if __name__ == "__main__":
    test_chat_model()
