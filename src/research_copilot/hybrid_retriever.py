from __future__ import annotations

import re

from research_copilot.keyword_retriever import search_chunks
from research_copilot.semantic_retriever import (
    EmbeddingModel,
    semantic_search_chunks,
)

Chunk = dict[str, int | str]
HybridResult = dict[str, int | float | str]

RRF_K = 60


def hybrid_search_chunks(
    query: str,
    chunks: list[Chunk],
    embedding_model: EmbeddingModel,
    limit: int = 5,
    candidate_limit: int | None = None,
) -> list[HybridResult]:
    if limit <= 0 or not query.strip() or not chunks:
        return []

    pool_size = candidate_limit or max(limit * 4, 20)
    keyword_results = search_chunks(query, chunks, limit=pool_size)
    semantic_results = semantic_search_chunks(
        query,
        chunks,
        embedding_model,
        limit=pool_size,
    )

    candidates: dict[tuple[int, int], HybridResult] = {}

    for rank, result in enumerate(keyword_results, start=1):
        key = _result_key(result)
        candidate = candidates.setdefault(key, _base_result(result))
        candidate["keyword_rank"] = rank
        candidate["keyword_score"] = float(result["score"])
        candidate["fusion_score"] = float(candidate["fusion_score"]) + (
            0.8 / (RRF_K + rank)
        )

    for rank, result in enumerate(semantic_results, start=1):
        key = _result_key(result)
        candidate = candidates.setdefault(key, _base_result(result))
        candidate["semantic_rank"] = rank
        candidate["semantic_score"] = float(result["score"])
        candidate["fusion_score"] = float(candidate["fusion_score"]) + (
            1.0 / (RRF_K + rank)
        )

    for candidate in candidates.values():
        text = str(candidate["text"])
        penalty = reference_penalty(text)
        bonus = body_text_bonus(text) + lexical_overlap_bonus(query, text)
        candidate["reference_penalty"] = penalty
        candidate["rerank_score"] = (
            float(candidate["fusion_score"]) + bonus - penalty
        )
        candidate["score"] = float(candidate["rerank_score"])

    ranked = sorted(
        candidates.values(),
        key=lambda item: (
            -float(item["rerank_score"]),
            int(item["source_page"]),
            int(item["chunk_index"]),
        ),
    )
    return ranked[:limit]


def reference_penalty(text: str) -> float:
    normalized = text.casefold()
    penalty = 0.0

    if re.search(r"(^|\n)\s*references\s*($|\n)", normalized):
        penalty += 0.035

    bibliography_signals = sum(
        signal in normalized
        for signal in (
            "arxiv preprint",
            "proceedings of",
            "international conference on",
            "transactions on",
        )
    )
    numbered_citations = len(re.findall(r"\[\d+\]", text))
    if bibliography_signals >= 2 or numbered_citations >= 6:
        penalty += 0.02

    if "equal contribution" in normalized or "work performed while" in normalized:
        penalty += 0.02

    return penalty


def body_text_bonus(text: str) -> float:
    normalized = text.casefold()
    section_signals = (
        "introduction",
        "background",
        "model architecture",
        "we propose",
        "we use",
        "we apply",
    )
    return 0.004 if any(signal in normalized for signal in section_signals) else 0.0


def lexical_overlap_bonus(query: str, text: str) -> float:
    query_terms = {
        term.casefold()
        for term in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", query)
    }
    if not query_terms:
        return 0.0

    normalized_text = text.casefold()
    matched_terms = sum(term in normalized_text for term in query_terms)
    return 0.004 * matched_terms / len(query_terms)


def _result_key(result: dict[str, int | float | str]) -> tuple[int, int]:
    return int(result["source_page"]), int(result["chunk_index"])


def _base_result(result: dict[str, int | float | str]) -> HybridResult:
    return {
        "source_page": int(result["source_page"]),
        "chunk_index": int(result["chunk_index"]),
        "text": str(result["text"]),
        "score": 0.0,
        "keyword_rank": 0,
        "keyword_score": 0.0,
        "semantic_rank": 0,
        "semantic_score": 0.0,
        "fusion_score": 0.0,
        "reference_penalty": 0.0,
        "rerank_score": 0.0,
    }
