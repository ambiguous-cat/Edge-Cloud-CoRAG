import os
import requests
import openai
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件

# 读取 Ollama 和 OpenAI 配置
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip('/')  # 去除末尾斜杠
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_EMBEDDING_TYPE = os.getenv("EMBEDDING_TYPE", "bge").strip().lower() or "bge"
# DEFAULT_EMBEDDING_MODEL = (
#     os.getenv("EMBEDDING_MODEL", "bge-large:latest").strip() or "bge-large:latest"
# )
DEFAULT_EMBEDDING_MODEL="bge-m3:latest"
# 支持的嵌入类型：
# text -> OpenAI 兼容嵌入接口
# bge/qwen -> Ollama /api/embeddings
embedding_models = ['text', 'bge', 'qwen']
embedding_model = (
    DEFAULT_EMBEDDING_TYPE if DEFAULT_EMBEDDING_TYPE in embedding_models else 'bge'
)

def get_embedding(text):
    if embedding_model not in embedding_models:
        return 0
    elif embedding_model == 'text':
        return get_openai_embedding(text, model=DEFAULT_EMBEDDING_MODEL)
    elif embedding_model == 'bge':
        return get_ollama_embedding(text, model=DEFAULT_EMBEDDING_MODEL)
    elif embedding_model == 'qwen':
        return get_qwen3_embedding(text, model=DEFAULT_EMBEDDING_MODEL)

def get_embeddings(texts):
    if embedding_model not in embedding_models:
        return 0
    elif embedding_model == 'text':
        return get_openai_embeddings(texts, model=DEFAULT_EMBEDDING_MODEL)
    elif embedding_model == 'bge':
        return get_ollama_embeddings(texts, model=DEFAULT_EMBEDDING_MODEL)
    elif embedding_model == 'qwen':
        return get_qwen3_embeddings(texts, model=DEFAULT_EMBEDDING_MODEL)


def get_ollama_embedding(text, model=None):
    """
    调用本地 Ollama 的嵌入模型，获取单条文本的嵌入向量。
    """
    model_name = (model or DEFAULT_EMBEDDING_MODEL).strip()
    url = f"{OLLAMA_HOST}/api/embeddings"
    data = {
        "model": model_name,
        "prompt": text
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()["embedding"]

def get_ollama_embeddings(texts, model=None):
    """
    批量获取文本嵌入，返回二维数组。
    遇到异常时打印出错文本和错误信息。
    """
    model_name = (model or DEFAULT_EMBEDDING_MODEL).strip()
    results = []
    for i, text in enumerate(texts):
        try:
            results.append(get_ollama_embedding(text, model_name))
        except Exception as e:
            print(f"第{i+1}个分块出错，内容前30字：{text[:30]}... 错误信息：{e}")
            raise
    return results

# OpenAI 嵌入模型封装

def get_openai_embedding(text, model=None, api_key=None, api_base=None):
    """
    调用 OpenAI 的嵌入模型，获取单条文本的嵌入向量。
    """
    model_name = (model or DEFAULT_EMBEDDING_MODEL).strip()
    if api_key is None:
        api_key = OPENAI_API_KEY
    if api_base is None:
        api_base = OPENAI_API_BASE
    openai.api_key = api_key
    if api_base:
        openai.base_url = api_base
    response = openai.embeddings.create(
        input=text,
        model=model_name
    )
    return response.data[0].embedding

def get_openai_embeddings(texts, model=None, api_key=None, api_base=None):
    """
    批量获取文本嵌入，返回二维数组。
    """
    model_name = (model or DEFAULT_EMBEDDING_MODEL).strip()
    if api_key is None:
        api_key = OPENAI_API_KEY
    if api_base is None:
        api_base = OPENAI_API_BASE
    openai.api_key = api_key
    if api_base:
        openai.base_url = api_base
    response = openai.embeddings.create(
        input=texts,
        model=model_name
    )
    return [item.embedding for item in response.data]

# Qwen3-Embedding-4B Ollama嵌入

def get_qwen3_embedding(text, model=None):
    """
    调用 Ollama 的 Qwen3-Embedding-4B 模型
    """
    return get_ollama_embedding(text, model=model)

def get_qwen3_embeddings(texts, model=None):
    """
    批量获取文本嵌入，返回二维数组。
    """
    return get_ollama_embeddings(texts, model=model)
