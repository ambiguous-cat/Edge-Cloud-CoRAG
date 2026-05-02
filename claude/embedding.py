import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Embedding config: keep it simple, one URL + one key.
EMBEDDING_URL = os.getenv("EMBEDDING_API_URL", "https://open.bigmodel.cn/api/paas/v4/embeddings")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")

# Compatibility export for old imports.
API_KEY = EMBEDDING_API_KEY

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embedding-3")
embedding_models = [m.strip() for m in os.getenv("EMBEDDING_MODELS", DEFAULT_EMBEDDING_MODEL).split(",") if m.strip()]
embedding_model = embedding_models[0] if embedding_models else DEFAULT_EMBEDDING_MODEL

DEFAULT_DIMENSIONS = int(os.getenv("DIMENSION", "2048"))
_request_dimensions_raw = os.getenv("EMBEDDING_REQUEST_DIMENSIONS", "").strip()
DEFAULT_REQUEST_DIMENSIONS = int(_request_dimensions_raw) if _request_dimensions_raw else None
DEFAULT_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", "120"))


def get_embedding(text: str):
    return get_text_embedding(text, model=embedding_model)


def get_embeddings(texts: List[str]):
    return get_text_embeddings(texts, model=embedding_model)


def get_text_embedding(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
    api_key: Optional[str] = None,
    dimensions: Optional[int] = None,
):
    if api_key is None:
        api_key = EMBEDDING_API_KEY
    if not api_key:
        raise ValueError("Embedding API key is missing, set EMBEDDING_API_KEY in .env")

    final_dimensions = DEFAULT_REQUEST_DIMENSIONS if dimensions is None else dimensions
    payload = {"model": model, "input": text}
    if final_dimensions is not None:
        payload["dimensions"] = final_dimensions
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    response = requests.post(EMBEDDING_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    result = response.json()

    if "data" not in result or not result["data"]:
        raise ValueError(f"Unexpected API response format: {result}")
    return result["data"][0]["embedding"]


def get_text_embeddings(
    texts: List[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    api_key: Optional[str] = None,
    dimensions: Optional[int] = None,
):
    if api_key is None:
        api_key = EMBEDDING_API_KEY
    if not api_key:
        raise ValueError("Embedding API key is missing, set EMBEDDING_API_KEY in .env")

    final_dimensions = DEFAULT_REQUEST_DIMENSIONS if dimensions is None else dimensions
    payload = {"model": model, "input": texts}
    if final_dimensions is not None:
        payload["dimensions"] = final_dimensions
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    response = requests.post(EMBEDDING_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    result = response.json()

    if "data" not in result or not result["data"]:
        raise ValueError(f"Unexpected API response format: {result}")
    return [item["embedding"] for item in result["data"]]


def set_embedding_model(model_name: str):
    global embedding_model
    if not model_name or not model_name.strip():
        raise ValueError("model_name cannot be empty")
    embedding_model = model_name.strip()
    if embedding_model not in embedding_models:
        embedding_models.append(embedding_model)
    print(f"embedding model switched to: {embedding_model}")


def get_current_embedding_model() -> str:
    return embedding_model


def get_available_embedding_models() -> List[str]:
    return embedding_models.copy()


def test_embedding_model():
    print("=== Embedding Model Test ===")
    print(f"current model: {get_current_embedding_model()}")
    print(f"embedding url: {EMBEDDING_URL}")
    if not EMBEDDING_API_KEY:
        print("EMBEDDING_API_KEY missing, check .env")
        return False

    try:
        vec = get_embedding("This is a test text for embedding.")
        print(f"single embedding ok, dim: {len(vec)}")
        vecs = get_embeddings(["first test text", "second test text"])
        print(f"batch embedding ok, count: {len(vecs)}, dim: {len(vecs[0]) if vecs else 0}")
        return True
    except Exception as exc:
        print(f"test failed: {exc}")
        return False


if __name__ == "__main__":
    test_embedding_model()
