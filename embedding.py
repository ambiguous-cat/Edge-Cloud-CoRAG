import os
import requests
import openai
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件

# 读取 Ollama 和 OpenAI 配置
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip('/')  # 去除末尾斜杠
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ollama 本地嵌入
embedding_models=['text','bge','qwen']
embedding_model=embedding_models[1]  # 使用BGE本地嵌入模型

def get_embedding(text):
    if embedding_model not in embedding_models:
        return 0
    elif(embedding_model=='text'):
        return (get_openai_embedding(text))
    elif(embedding_model=='bge'):
        return (get_ollama_embedding(text))
    elif(embedding_model=='qwen'):
        return (get_qwen3_embedding(text))

def get_embeddings(texts):
    if embedding_model not in embedding_models:
        return 0
    elif(embedding_model=='text'):
        return (get_openai_embeddings(texts))
    elif(embedding_model=='bge'):
        return (get_ollama_embeddings(texts))
    elif(embedding_model=='qwen'):
        return (get_qwen3_embeddings(texts))
def get_ollama_embedding(text, model="bge-large"):
    """
    调用本地 Ollama 的嵌入模型，获取单条文本的嵌入向量。
    """
    url = f"{OLLAMA_HOST}/api/embeddings"
    data = {
        "model": model,
        "prompt": text
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()["embedding"]

def get_ollama_embeddings(texts, model="bge-large"):
    """
    批量获取文本嵌入，返回二维数组。
    遇到异常时打印出错文本和错误信息。
    """
    results = []
    for i, text in enumerate(texts):
        try:
            results.append(get_ollama_embedding(text, model))
        except Exception as e:
            print(f"第{i+1}个分块出错，内容前30字：{text[:30]}... 错误信息：{e}")
            raise
    return results

# OpenAI 嵌入模型封装

def get_openai_embedding(text, model="text-embedding-ada-002", api_key=None, api_base=None):
    """
    调用 OpenAI 的嵌入模型，获取单条文本的嵌入向量。
    """
    if api_key is None:
        api_key = OPENAI_API_KEY
    if api_base is None:
        api_base = OPENAI_API_BASE
    openai.api_key = api_key
    if api_base:
        openai.base_url = api_base
    response = openai.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

def get_openai_embeddings(texts, model="text-embedding-ada-002", api_key=None, api_base=None):
    """
    批量获取文本嵌入，返回二维数组。
    """
    if api_key is None:
        api_key = OPENAI_API_KEY
    if api_base is None:
        api_base = OPENAI_API_BASE
    openai.api_key = api_key
    if api_base:
        openai.base_url = api_base
    response = openai.embeddings.create(
        input=texts,
        model=model
    )
    return [item.embedding for item in response.data]

# Qwen3-Embedding-4B Ollama嵌入

def get_qwen3_embedding(text, model="dengcao/Qwen3-Embedding-4B:Q4_K_M"):
    """
    调用 Ollama 的 Qwen3-Embedding-4B 模型
    """
    url = f"{OLLAMA_HOST}/api/embeddings"
    data = {
        "model": model,
        "prompt": text
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()["embedding"]

def get_qwen3_embeddings(texts, model="dengcao/Qwen3-Embedding-4B:Q4_K_M"):
    """
    批量获取文本嵌入，返回二维数组。
    """
    results = []
    for i, text in enumerate(texts):
        try:
            results.append(get_qwen3_embedding(text, model))
        except Exception as e:
            print(f"第{i+1}个分块出错，内容前30字：{text[:30]}... 错误信息：{e}")
            raise
    return results
