"""Model-agnostic helpers for the offline reranker experiment."""

from __future__ import annotations

import math
import re
import unicodedata
from time import monotonic
from typing import Any, Callable, Protocol, Sequence

from research_copilot.hybrid_retriever import hybrid_search_chunks


class PairScorer(Protocol):
    def predict(
        self, pairs: Sequence[tuple[str, str]], *, batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[float]: ...


def top_distinct_pages(
    hits: list[dict[str, int | float | str]], limit: int,
) -> list[int]:
    return [
        int(hit["source_page"])
        for hit in top_distinct_hits(hits, limit)
    ]


def top_distinct_hits(
    hits: list[dict[str, int | float | str]], limit: int,
) -> list[dict[str, int | float | str]]:
    selected: list[dict[str, int | float | str]] = []
    pages: set[int] = set()
    for hit in hits:
        page = int(hit["source_page"])
        if page in pages:
            continue
        pages.add(page)
        selected.append(hit)
        if len(selected) == limit:
            break
    return selected


def normalize_evidence_text(value: str) -> str:
    """Normalize extracted PDF text without changing its semantic content."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def evidence_requirement_coverage(
    hits: Sequence[dict[str, int | float | str]],
    requirements: Sequence[Sequence[str]] | None,
    limit: int,
    *,
    require_one_page: bool = False,
) -> dict[str, int | bool] | None:
    """Measure deterministic phrase-group coverage across an evidence set.

    Every outer group is required; any normalized phrase inside a group may
    satisfy that group. This is a narrow answer-bearing-span diagnostic, not a
    general semantic sufficiency or abstention score.
    """
    if requirements is None:
        return None
    if not requirements:
        raise ValueError("Evidence requirements must contain at least one group.")
    normalized_groups: list[list[str]] = []
    for group in requirements:
        alternatives = [normalize_evidence_text(str(phrase)) for phrase in group]
        if not alternatives or any(not phrase for phrase in alternatives):
            raise ValueError("Every evidence requirement group needs a phrase.")
        normalized_groups.append(alternatives)
    selected = hits[:limit]
    if require_one_page:
        by_page: dict[int, list[str]] = {}
        for hit in selected:
            by_page.setdefault(int(hit["source_page"]), []).append(
                str(hit.get("text", ""))
            )
        evidence_views = [
            normalize_evidence_text(" ".join(page_texts))
            for page_texts in by_page.values()
        ]
    else:
        evidence_views = [
            normalize_evidence_text(
                " ".join(str(hit.get("text", "")) for hit in selected)
            )
        ]
    matched_by_view = [
        [
            any(phrase in evidence for phrase in alternatives)
            for alternatives in normalized_groups
        ]
        for evidence in evidence_views
    ]
    matched = max(matched_by_view, key=sum, default=[False] * len(normalized_groups))
    return {
        "matched_groups": sum(matched),
        "total_groups": len(matched),
        "complete": all(matched),
    }


def evaluate_case(
    case: dict[str, Any],
    chunks: list[dict[str, int | str]],
    embedding_model: Any,
    model: PairScorer,
    *,
    top_k: int = 5,
    candidate_limit: int = 30,
    candidate_search: Callable[..., list[dict[str, int | float | str]]] = (
        hybrid_search_chunks
    ),
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Evaluate one frozen case without coupling tests to the CLI script."""
    start = clock()
    candidates = candidate_search(
        case["query"], chunks, embedding_model, limit=candidate_limit,
    )
    retrieval_seconds = clock() - start
    start = clock()
    reranked = rerank_candidates(case["query"], candidates, model)
    rerank_seconds = clock() - start
    anchors = set(case["anchor_pages"])
    irrelevant = set(case["known_irrelevant_pages"])
    baseline_pages = [int(hit["source_page"]) for hit in candidates[:top_k]]
    reranked_pages = [int(hit["source_page"]) for hit in reranked[:top_k]]
    distinct_hits = top_distinct_hits(reranked, top_k)
    distinct_pages = [int(hit["source_page"]) for hit in distinct_hits]
    requirements = case.get("evidence_requirements")
    require_one_page = bool(case.get("evidence_must_share_page", False))

    def first_anchor_rank(
        hits: list[dict[str, int | float | str]],
    ) -> int | None:
        return next(
            (
                rank
                for rank, hit in enumerate(hits, start=1)
                if int(hit["source_page"]) in anchors
            ),
            None,
        )

    return {
        "id": case["id"],
        "paper": case["paper"],
        "language": case["language"],
        "kind": "answerable" if anchors else "no_answer",
        "anchor_pages": sorted(anchors),
        "anchor_in_candidates": (
            bool(
                anchors.intersection(
                    int(hit["source_page"]) for hit in candidates
                )
            )
            if anchors
            else None
        ),
        "baseline_first_anchor_rank": (
            first_anchor_rank(candidates) if anchors else None
        ),
        "reranked_first_anchor_rank": (
            first_anchor_rank(reranked) if anchors else None
        ),
        "baseline_pages_at_5": baseline_pages,
        "reranked_pages_at_5": reranked_pages,
        "distinct_pages_at_5": distinct_pages,
        "baseline_anchor_at_5": (
            bool(anchors.intersection(baseline_pages)) if anchors else None
        ),
        "reranked_anchor_at_5": (
            bool(anchors.intersection(reranked_pages)) if anchors else None
        ),
        "distinct_anchor_at_5": (
            bool(anchors.intersection(distinct_pages)) if anchors else None
        ),
        "baseline_known_irrelevant_at_5": sum(
            page in irrelevant for page in baseline_pages
        ),
        "reranked_known_irrelevant_at_5": sum(
            page in irrelevant for page in reranked_pages
        ),
        "distinct_known_irrelevant_at_5": sum(
            page in irrelevant for page in distinct_pages
        ),
        "top_cross_encoder_score": (
            float(reranked[0]["cross_encoder_score"]) if reranked else None
        ),
        "candidate_evidence_coverage": evidence_requirement_coverage(
            candidates, requirements, candidate_limit,
            require_one_page=require_one_page,
        ),
        "baseline_evidence_coverage_at_1": evidence_requirement_coverage(
            candidates, requirements, 1,
            require_one_page=require_one_page,
        ),
        "reranked_evidence_coverage_at_1": evidence_requirement_coverage(
            reranked, requirements, 1,
            require_one_page=require_one_page,
        ),
        "baseline_evidence_coverage_at_5": evidence_requirement_coverage(
            candidates, requirements, top_k,
            require_one_page=require_one_page,
        ),
        "reranked_evidence_coverage_at_5": evidence_requirement_coverage(
            reranked, requirements, top_k,
            require_one_page=require_one_page,
        ),
        "distinct_evidence_coverage_at_5": evidence_requirement_coverage(
            distinct_hits, requirements, top_k,
            require_one_page=require_one_page,
        ),
        "retrieval_seconds": round(retrieval_seconds, 3),
        "rerank_seconds": round(rerank_seconds, 3),
    }


def rerank_candidates(
    query: str,
    candidates: list[dict[str, int | float | str]],
    model: PairScorer,
) -> list[dict[str, int | float | str]]:
    """Score only retrieved candidates; never search the full PDF with this model."""
    if not candidates:
        return []
    pairs = [(query, str(hit["text"])) for hit in candidates]
    scores = model.predict(pairs, batch_size=8, show_progress_bar=False)
    if len(scores) != len(candidates):
        raise ValueError("Cross Encoder score count does not match candidate count.")
    ranked = []
    for original_rank, (hit, value) in enumerate(zip(candidates, scores, strict=True)):
        score = float(value)
        if not math.isfinite(score):
            raise ValueError("Cross Encoder returned a non-finite score.")
        ranked.append((original_rank, {**hit, "cross_encoder_score": score}))
    ranked.sort(key=lambda item: (-float(item[1]["cross_encoder_score"]), item[0]))
    return [hit for _, hit in ranked]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [result for result in results if result["kind"] == "answerable"]
    negatives = [result for result in results if result["kind"] == "no_answer"]
    by_language: dict[str, dict[str, int]] = {}
    for language in sorted({case["language"] for case in positives}):
        language_cases = [case for case in positives if case["language"] == language]
        by_language[language] = {
            "positive_cases": len(language_cases),
            "baseline_anchor_at_5": sum(
                case["baseline_anchor_at_5"] for case in language_cases
            ),
            "reranked_anchor_at_5": sum(
                case["reranked_anchor_at_5"] for case in language_cases
            ),
        }
    evidence_cases = [
        result for result in positives
        if result.get("reranked_evidence_coverage_at_5") is not None
    ]

    def complete_count(field: str) -> int:
        return sum(bool(case[field]["complete"]) for case in evidence_cases)

    positive_scores = [
        float(result["top_cross_encoder_score"])
        for result in positives
        if result.get("top_cross_encoder_score") is not None
    ]
    negative_scores = [
        float(result["top_cross_encoder_score"])
        for result in negatives
        if result.get("top_cross_encoder_score") is not None
    ]
    positive_min = min(positive_scores) if positive_scores else None
    negative_max = max(negative_scores) if negative_scores else None

    return {
        "positive_cases": len(positives),
        "negative_cases": len(negatives),
        "anchor_in_candidates": sum(result["anchor_in_candidates"] for result in positives),
        "baseline_anchor_at_5": sum(result["baseline_anchor_at_5"] for result in positives),
        "reranked_anchor_at_5": sum(result["reranked_anchor_at_5"] for result in positives),
        "gains": sum(
            result["reranked_anchor_at_5"] and not result["baseline_anchor_at_5"]
            for result in positives
        ),
        "regressions": sum(
            result["baseline_anchor_at_5"] and not result["reranked_anchor_at_5"]
            for result in positives
        ),
        "baseline_known_irrelevant_at_5": sum(
            result["baseline_known_irrelevant_at_5"] for result in results
        ),
        "reranked_known_irrelevant_at_5": sum(
            result["reranked_known_irrelevant_at_5"] for result in results
        ),
        "negative_top_scores": {
            result["id"]: result["top_cross_encoder_score"] for result in negatives
        },
        "top_score_separation": {
            "positive_min": positive_min,
            "negative_max": negative_max,
            "single_threshold_separates": (
                negative_max < positive_min
                if positive_min is not None and negative_max is not None
                else None
            ),
        },
        "by_language": by_language,
        "no_answer_abstention_supported": False,
        "answer_bearing_evidence": {
            "cases": len(evidence_cases),
            "candidate_complete": complete_count("candidate_evidence_coverage"),
            "baseline_complete_at_1": complete_count(
                "baseline_evidence_coverage_at_1"
            ),
            "reranked_complete_at_1": complete_count(
                "reranked_evidence_coverage_at_1"
            ),
            "baseline_complete_at_5": complete_count(
                "baseline_evidence_coverage_at_5"
            ),
            "reranked_complete_at_5": complete_count(
                "reranked_evidence_coverage_at_5"
            ),
            "distinct_complete_at_5": complete_count(
                "distinct_evidence_coverage_at_5"
            ),
        },
    }
