import json
import logging
import os
import re
from typing import Dict, List, Any

from dotenv import load_dotenv

import chat_model

load_dotenv()
logger = logging.getLogger("paper_search.query_planner")

DEFAULT_MAX_QUERIES = int(os.getenv("PAPER_SEARCH_MAX_QUERIES", "3"))
DEFAULT_HISTORY_MESSAGES = int(os.getenv("PAPER_SEARCH_HISTORY_MESSAGES", "8"))


def _extract_json(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _normalize_history(history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    normalized = []
    for msg in history or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = str(msg.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized[-DEFAULT_HISTORY_MESSAGES:]


def _fallback_queries(history: List[Dict[str, str]], max_queries: int) -> Dict[str, Any]:
    last_user_message = ""
    for msg in reversed(history):
        if msg.get("role") == "user" and msg.get("content") != "/论文检索":
            last_user_message = msg.get("content", "")
            break

    query = last_user_message.strip() or "retrieval augmented generation large language models"
    return {
        "queries": [query[:120]][:max_queries],
        "reason": "LLM query planning failed; using the latest user topic as fallback.",
    }


def build_paper_search_plan(history: List[Dict[str, str]] = None, max_queries: int = None) -> Dict[str, Any]:
    """Generate English arXiv search queries from recent conversation history."""
    max_queries = max(1, int(max_queries or DEFAULT_MAX_QUERIES))
    normalized_history = _normalize_history(history)
    logger.info("paper query planning started | history_messages=%s | max_queries=%s", len(normalized_history), max_queries)

    prompt = {
        "task": "Generate arXiv paper search queries from the recent conversation.",
        "requirements": [
            "Output JSON only.",
            f"Generate 1 to {max_queries} English search queries.",
            "Each query should be 4 to 12 words.",
            "Use academic keywords, not full questions.",
            "Preserve model names, dataset names, methods, and domain terms.",
            "If the context is weak, infer the broadest likely research topic.",
        ],
        "output_schema": {
            "queries": ["retrieval augmented generation reranking"],
            "reason": "short Chinese reason",
        },
        "history": normalized_history,
    }

    messages = [
        {"role": "system", "content": "你是学术论文检索 query 规划器，只输出 JSON。"},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
    ]

    try:
        response = chat_model.chat(messages, temperature=0, max_tokens=500)
        logger.info("paper query planner LLM response received | chars=%s", len(response))
        data = _extract_json(response)
        queries = []
        for query in data.get("queries", []):
            query_text = str(query).strip()
            if query_text and query_text not in queries:
                queries.append(query_text)
        if not queries:
            logger.warning("paper query planner returned no queries, using fallback")
            return _fallback_queries(normalized_history, max_queries)
        logger.info("paper query planning done | queries=%s | reason=%s", queries[:max_queries], data.get("reason", ""))
        return {
            "queries": queries[:max_queries],
            "reason": str(data.get("reason", "")).strip(),
        }
    except Exception as exc:
        logger.exception("paper query planning failed, using fallback")
        fallback = _fallback_queries(normalized_history, max_queries)
        fallback["error"] = str(exc)
        return fallback
