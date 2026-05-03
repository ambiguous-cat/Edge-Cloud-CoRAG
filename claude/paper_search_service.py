import json
import logging
import os
import time
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

import arxiv_mcp_client
import paper_query_planner
import reranker

load_dotenv()
logger = logging.getLogger("paper_search.service")

PAPER_SEARCH_PER_QUERY = int(os.getenv("PAPER_SEARCH_PER_QUERY", "3"))
PAPER_SEARCH_MAX_PAPERS = int(os.getenv("PAPER_SEARCH_MAX_PAPERS", "8"))
PAPER_SEARCH_MAX_QUERIES = int(os.getenv("PAPER_SEARCH_MAX_QUERIES", "3"))
PAPER_SEARCH_USE_RERANK = os.getenv("PAPER_SEARCH_USE_RERANK", "true").strip().lower() in {"1", "true", "yes", "on"}


def _author_names(authors: Any) -> List[str]:
    names = []
    for author in authors or []:
        if isinstance(author, dict):
            name = str(author.get("name", "")).strip()
        else:
            name = str(author).strip()
        if name:
            names.append(name)
    return names


def _normalize_paper(raw: Dict[str, Any], query: str) -> Dict[str, Any]:
    summary = str(raw.get("summary", "")).strip()
    return {
        "id": str(raw.get("id", "")).strip(),
        "title": str(raw.get("title", "")).strip(),
        "authors": _author_names(raw.get("authors", [])),
        "published": str(raw.get("published", "")).strip(),
        "summary": summary,
        "url": str(raw.get("url", "")).strip(),
        "source": "arxiv",
        "matched_query": query,
        "similarity_score": 1.0,
        "content": summary,
    }


def _dedupe_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for paper in papers:
        key = paper.get("id") or paper.get("url") or paper.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(paper)
    return deduped


def _search_one_query(query: str, max_results: int) -> List[Dict[str, Any]]:
    start_time = time.time()
    logger.info("arxiv search started | query=%s | max_results=%s", query, max_results)
    result = arxiv_mcp_client.call_tool("search_arxiv_json", {
        "query": query,
        "maxResults": max_results,
    })
    text = arxiv_mcp_client.extract_text_content(result)
    logger.info("arxiv MCP text received | query=%s | chars=%s", query, len(text))
    data = json.loads(text)
    papers = [_normalize_paper(paper, query) for paper in data.get("papers", [])]
    logger.info(
        "arxiv search done | query=%s | result_count=%s | total_results=%s | elapsed=%.2fs",
        query,
        len(papers),
        data.get("totalResults"),
        time.time() - start_time,
    )
    return papers


def search_papers_from_context(history: List[Dict[str, str]] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    start_time = time.time()
    logger.info("paper search started | history_messages=%s", len(history or []))
    plan = paper_query_planner.build_paper_search_plan(history, max_queries=PAPER_SEARCH_MAX_QUERIES)
    logger.info("paper search plan ready | queries=%s | reason=%s | planner_error=%s", plan.get("queries", []), plan.get("reason", ""), plan.get("error"))
    papers: List[Dict[str, Any]] = []
    errors = []

    for query in plan.get("queries", []):
        try:
            query_papers = _search_one_query(query, PAPER_SEARCH_PER_QUERY)
            papers.extend(query_papers)
        except Exception as exc:
            logger.exception("arxiv search failed | query=%s", query)
            errors.append({"query": query, "error": str(exc)})

    before_dedupe = len(papers)
    papers = _dedupe_papers(papers)
    logger.info("paper search dedupe done | before=%s | after=%s", before_dedupe, len(papers))

    if PAPER_SEARCH_USE_RERANK and papers:
        try:
            logger.info("paper rerank started | paper_count=%s", len(papers))
            rerank_docs = [
                {
                    "title": paper.get("title", ""),
                    "content": paper.get("summary", ""),
                    "source": paper.get("url", ""),
                    "similarity_score": paper.get("similarity_score", 1.0),
                }
                for paper in papers
            ]
            ranked_docs = reranker.rerank(" ".join(plan.get("queries", [])), rerank_docs, top_n=len(rerank_docs))
            title_to_rank = {doc.get("title"): index for index, doc in enumerate(ranked_docs)}
            papers.sort(key=lambda paper: title_to_rank.get(paper.get("title"), len(papers)))
            logger.info("paper rerank done | ranked_count=%s", len(ranked_docs))
        except Exception as exc:
            logger.exception("paper rerank failed, keeping arxiv order")
            errors.append({"query": "rerank", "error": str(exc)})

    plan["errors"] = errors
    final_papers = papers[:PAPER_SEARCH_MAX_PAPERS]
    logger.info(
        "paper search done | final_count=%s | errors=%s | elapsed=%.2fs",
        len(final_papers),
        len(errors),
        time.time() - start_time,
    )
    return plan, final_papers


def papers_to_documents(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    documents = []
    for index, paper in enumerate(papers, 1):
        authors = ", ".join(paper.get("authors", [])[:8])
        content = (
            f"标题: {paper.get('title', '')}\n"
            f"作者: {authors}\n"
            f"发布日期: {paper.get('published', '')}\n"
            f"arXiv ID: {paper.get('id', '')}\n"
            f"链接: {paper.get('url', '')}\n"
            f"摘要: {paper.get('summary', '')}"
        )
        documents.append({
            "title": paper.get("title") or f"arXiv Paper {index}",
            "content": content,
            "source": paper.get("url", "arxiv"),
            "similarity_score": paper.get("similarity_score", 1.0),
        })
    return documents
