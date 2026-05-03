import json
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Rerank config: native rerank endpoint or OpenAI-compatible chat/completions proxy.
RERANK_ENABLED = _env_bool("RERANK_ENABLED", True)
RERANK_URL = os.getenv("RERANK_API_URL", "")
RERANK_API_KEY = os.getenv("RERANK_API_KEY", "")
RERANK_API_TYPE = os.getenv("RERANK_API_TYPE", "auto").strip().lower()

# Compatibility export for old imports if this module is reused elsewhere.
API_KEY = RERANK_API_KEY

DEFAULT_RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-reranker-8b")
rerank_models = [m.strip() for m in os.getenv("RERANK_MODELS", DEFAULT_RERANK_MODEL).split(",") if m.strip()]
rerank_model = rerank_models[0] if rerank_models else DEFAULT_RERANK_MODEL

DEFAULT_TIMEOUT = int(os.getenv("RERANK_TIMEOUT", "60"))
DEFAULT_TEMPERATURE = float(os.getenv("RERANK_TEMPERATURE", "0"))
DEFAULT_MAX_TOKENS = int(os.getenv("RERANK_MAX_TOKENS", "2048"))
DEFAULT_CANDIDATE_MULTIPLIER = int(os.getenv("RERANK_CANDIDATE_MULTIPLIER", "8"))
DEFAULT_MAX_CANDIDATES = int(os.getenv("RERANK_MAX_CANDIDATES", "50"))
DEFAULT_DOCUMENT_MAX_CHARS = int(os.getenv("RERANK_DOCUMENT_MAX_CHARS", "1600"))


def is_rerank_enabled() -> bool:
    return RERANK_ENABLED and bool(RERANK_URL and RERANK_API_KEY and rerank_model)


def get_candidate_multiplier() -> int:
    return max(1, DEFAULT_CANDIDATE_MULTIPLIER)


def get_max_candidates() -> int:
    return max(1, DEFAULT_MAX_CANDIDATES)


def _document_text(document: Dict[str, Any]) -> str:
    title = str(document.get("title", "")).strip()
    content = str(document.get("content", "")).strip()
    source = str(document.get("source", "")).strip()

    parts = []
    if title:
        parts.append(f"标题: {title}")
    if source:
        parts.append(f"来源: {source}")
    if content:
        parts.append(f"内容: {content}")

    text = "\n".join(parts) or content or title
    return text[:DEFAULT_DOCUMENT_MAX_CHARS]


def _is_native_rerank_endpoint() -> bool:
    if RERANK_API_TYPE in {"native", "rerank"}:
        return True
    if RERANK_API_TYPE in {"chat", "chat_completions", "chat-completions"}:
        return False
    return "/rerank" in RERANK_URL.rstrip("/").lower()


def _build_messages(query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    doc_lines = []
    for index, document in enumerate(documents):
        doc_lines.append(f"[{index}]\n{_document_text(document)}")

    user_prompt = (
        "请作为重排序模型，判断每个候选文档与查询的相关性。\n"
        "只返回 JSON，不要返回解释、Markdown 或额外文字。\n"
        "JSON 格式必须是："
        '{"results":[{"index":0,"relevance_score":0.0}]}\n'
        "relevance_score 取值范围为 0 到 1，越大表示越相关。\n\n"
        f"查询：{query}\n\n"
        "候选文档：\n"
        + "\n\n".join(doc_lines)
    )

    return [
        {"role": "system", "content": "你是一个严格输出 JSON 的检索重排序模型。"},
        {"role": "user", "content": user_prompt},
    ]


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", stripped, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Rerank response is not JSON: {text[:200]}")
    return json.loads(match.group(1))


def _normalize_results(raw: Any) -> List[Dict[str, float]]:
    if isinstance(raw, dict):
        raw_results = raw.get("results") or raw.get("data") or raw.get("scores") or []
    else:
        raw_results = raw

    results: List[Dict[str, float]] = []
    if not isinstance(raw_results, list):
        return results

    for fallback_index, item in enumerate(raw_results):
        if isinstance(item, dict):
            index = item.get("index", item.get("document_index", item.get("id", fallback_index)))
            score = item.get(
                "relevance_score",
                item.get("score", item.get("rerank_score", item.get("similarity_score"))),
            )
        else:
            index = fallback_index
            score = item

        try:
            parsed_index = int(index)
            parsed_score = float(score)
        except (TypeError, ValueError):
            continue

        results.append({"index": parsed_index, "relevance_score": parsed_score})

    return results


def _call_native_rerank_api(
    query: str,
    documents: List[Dict[str, Any]],
    model: Optional[str] = None,
) -> List[Dict[str, float]]:
    if not RERANK_URL:
        raise ValueError("RERANK_API_URL is missing, set it in .env")
    if not RERANK_API_KEY:
        raise ValueError("RERANK_API_KEY is missing, set it in .env")

    payload = {
        "model": model or rerank_model,
        "query": query,
        "documents": [_document_text(document) for document in documents],
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {RERANK_API_KEY}"}

    response = requests.post(RERANK_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    if response.status_code >= 400:
        raise requests.HTTPError(
            f"{response.status_code} Error from rerank API: {response.text[:500]}",
            response=response,
        )

    return _normalize_results(response.json())


def _call_chat_rerank_api(
    query: str,
    documents: List[Dict[str, Any]],
    model: Optional[str] = None,
) -> List[Dict[str, float]]:
    if not RERANK_URL:
        raise ValueError("RERANK_API_URL is missing, set it in .env")
    if not RERANK_API_KEY:
        raise ValueError("RERANK_API_KEY is missing, set it in .env")

    payload = {
        "model": model or rerank_model,
        "messages": _build_messages(query, documents),
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "stream": False,
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {RERANK_API_KEY}"}

    response = requests.post(RERANK_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    result = response.json()

    if "results" in result:
        return _normalize_results(result)

    if "choices" not in result or not result["choices"]:
        raise ValueError(f"Unexpected rerank API response format: {result}")

    content = result["choices"][0].get("message", {}).get("content", "")
    if not content:
        raise ValueError(f"Rerank response content is empty: {result}")

    return _normalize_results(_extract_json(content))


def _call_rerank_api(query: str, documents: List[Dict[str, Any]], model: Optional[str] = None) -> List[Dict[str, float]]:
    if _is_native_rerank_endpoint():
        return _call_native_rerank_api(query, documents, model=model)
    return _call_chat_rerank_api(query, documents, model=model)


def rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_n: Optional[int] = None,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not documents:
        return []

    limit = len(documents) if top_n is None else max(1, int(top_n))
    candidates = [dict(document) for document in documents]

    if not is_rerank_enabled():
        return candidates[:limit]

    results = _call_rerank_api(query, candidates, model=model)
    score_by_index = {item["index"]: item["relevance_score"] for item in results}

    scored_documents: List[Dict[str, Any]] = []
    unscored_documents: List[Dict[str, Any]] = []
    for index, document in enumerate(candidates):
        original_score = document.get("similarity_score")
        document["embedding_score"] = original_score

        if index in score_by_index:
            rerank_score = score_by_index[index]
            document["rerank_score"] = rerank_score
            document["similarity_score"] = rerank_score
            scored_documents.append(document)
        else:
            unscored_documents.append(document)

    scored_documents.sort(key=lambda item: item.get("rerank_score", float("-inf")), reverse=True)
    return (scored_documents + unscored_documents)[:limit]


def set_rerank_model(model_name: str):
    global rerank_model
    if not model_name or not model_name.strip():
        raise ValueError("model_name cannot be empty")
    rerank_model = model_name.strip()
    if rerank_model not in rerank_models:
        rerank_models.append(rerank_model)
    print(f"rerank model switched to: {rerank_model}")


def get_current_rerank_model() -> str:
    return rerank_model


def get_available_rerank_models() -> List[str]:
    return rerank_models.copy()


def test_rerank_model():
    print("=== Rerank Model Test ===")
    print(f"current model: {get_current_rerank_model()}")
    print(f"rerank url: {RERANK_URL}")
    if not is_rerank_enabled():
        print("rerank is disabled or config is incomplete, check .env")
        return False

    try:
        docs = [
            {"title": "苹果种植", "content": "苹果树需要充足阳光和合理修剪。", "similarity_score": 0.5},
            {"title": "量子计算", "content": "量子比特可以处于叠加态。", "similarity_score": 0.4},
        ]
        results = rerank("苹果树如何修剪？", docs, top_n=1)
        print(f"rerank ok, top title: {results[0].get('title') if results else 'N/A'}")
        return True
    except Exception as exc:
        print(f"test failed: {exc}")
        return False


if __name__ == "__main__":
    test_rerank_model()
