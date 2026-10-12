"""Deterministic scoring for the local M8.4a real-paper benchmark."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from research_copilot.hybrid_retriever import hybrid_search_chunks
from research_copilot.keyword_retriever import search_chunks
from research_copilot.library_organization import LibraryOrganizationStore
from research_copilot.page_store import load_page_data
from research_copilot.pdf_importer import import_pdf_to_json
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.semantic_retriever import (
    CachedEmbeddingModel,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_REVISION,
    E5EmbeddingModel,
    E5TokenAlignmentModel,
    EmbeddingModel,
    FineGrainedRelevanceModel,
    semantic_search_chunks,
)
from research_copilot.text_splitter import chunk_pages
from research_copilot.web_app import create_app


EVALUATION_MODEL_REVISION = DEFAULT_EMBEDDING_REVISION
EVIDENCE_GATE_THRESHOLDS = (0.80, 0.805, 0.81, 0.815, 0.82, 0.825, 0.83)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_papers(truth: dict[str, Any], paper_directory: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for alias, paper in truth["papers"].items():
        path = paper_directory / paper["filename"]
        if not path.is_file():
            raise ValueError(f"缺少真实 PDF：{path}")
        actual_sha = file_sha256(path)
        if actual_sha != paper["sha256"]:
            raise ValueError(f"PDF 版本或内容不符：{path} (SHA-256: {actual_sha})")
        paths[alias] = path
    return paths


def score_case(
    case: dict[str, Any],
    paper_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected_aliases = set(case["relevant_pages"])
    if set(paper_results) != expected_aliases:
        raise ValueError(f"{case['id']} 的结果没有严格保持论文范围。")

    details: dict[str, Any] = {}
    for alias, expected_pages in case["relevant_pages"].items():
        paper = paper_results[alias]
        hits = paper["hits"]
        returned_pages = [int(hit["source_page"]) for hit in hits]
        known_irrelevant = set(case["known_irrelevant_pages"][alias])
        scope_leakage_hits = sum(
            hit.get("paper_id") != paper.get("paper_id") for hit in hits
        )
        details[alias] = {
            "status": paper["status"],
            "returned_pages": returned_pages,
            "expected_anchor_pages": expected_pages,
            "source_found": bool(hits) if expected_pages else None,
            "anchor_found": bool(set(returned_pages) & set(expected_pages))
            if expected_pages
            else None,
            "correct_no_match": paper["status"] == "no_match"
            if not expected_pages
            else None,
            "known_irrelevant_hits": sum(
                page in known_irrelevant for page in returned_pages
            ),
            "scope_leakage_hits": scope_leakage_hits,
        }
    return {"id": case["id"], "query": case["query"], "papers": details}


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    all_papers = [paper for case in cases for paper in case["papers"].values()]
    positives = [paper for paper in all_papers if paper["source_found"] is not None]
    negatives = [paper for paper in all_papers if paper["correct_no_match"] is not None]
    returned_hit_count = sum(len(paper["returned_pages"]) for paper in all_papers)
    expected_source_count = len(positives)
    sources_found = sum(paper["source_found"] for paper in positives)
    anchor_pages_found = sum(paper["anchor_found"] for paper in positives)
    expected_no_match_count = len(negatives)
    correct_no_match_count = sum(
        paper["correct_no_match"] for paper in negatives
    )
    known_irrelevant_hits = sum(
        paper["known_irrelevant_hits"] for paper in all_papers
    )
    scope_leakage_hits = sum(
        paper["scope_leakage_hits"] for paper in all_papers
    )
    return {
        "expected_source_count": expected_source_count,
        "sources_found": sources_found,
        "source_coverage": sources_found / expected_source_count,
        "anchor_pages_found": anchor_pages_found,
        "anchor_coverage": anchor_pages_found / expected_source_count,
        "expected_no_match_count": expected_no_match_count,
        "correct_no_match_count": correct_no_match_count,
        "no_match_accuracy": correct_no_match_count / expected_no_match_count,
        "known_irrelevant_hits": known_irrelevant_hits,
        "returned_hit_count": returned_hit_count,
        "known_irrelevant_hit_rate": (
            known_irrelevant_hits / returned_hit_count if returned_hit_count else 0.0
        ),
        "scope_leakage_hits": scope_leakage_hits,
    }


def run(truth: dict[str, Any], paper_directory: Path) -> dict[str, Any]:
    paths = check_papers(truth, paper_directory)
    with TemporaryDirectory(prefix="research-copilot-m8-4a-") as temporary:
        root = Path(temporary)
        client = TestClient(
            create_app(
                paper_directory=paper_directory,
                processed_directory=root / "processed",
                frontend_directory=root / "web",
                history_store=ReadingHistoryStore(root / "history"),
                library_organization_store=LibraryOrganizationStore(
                    root / "organization"
                ),
            )
        )
        listed = client.get("/api/papers")
        listed.raise_for_status()
        ids_by_name = {paper["name"]: paper["id"] for paper in listed.json()}
        ids_by_alias = {
            alias: ids_by_name[path.name] for alias, path in paths.items()
        }

        cases: list[dict[str, Any]] = []
        for case in truth["cases"]:
            response = client.post(
                "/api/research/evidence",
                json={
                    "query": case["query"],
                    "paper_ids": list(ids_by_alias.values()),
                    "per_paper_limit": truth["per_paper_limit"],
                },
            )
            response.raise_for_status()
            returned = response.json()["papers"]
            if [paper["paper_id"] for paper in returned] != list(
                ids_by_alias.values()
            ):
                raise ValueError(f"{case['id']} 的论文范围或顺序发生变化。")
            by_alias = {
                alias: next(
                    paper for paper in returned if paper["paper_id"] == paper_id
                )
                for alias, paper_id in ids_by_alias.items()
            }
            cases.append(score_case(case, by_alias))

    check_papers(truth, paper_directory)
    return {
        "dataset_id": truth["dataset_id"],
        "per_paper_limit": truth["per_paper_limit"],
        "metrics": summarize(cases),
        "cases": cases,
    }


_CachedEmbeddingModel = CachedEmbeddingModel


def _top_distinct_pages(
    chunks: list[dict[str, int | float | str]],
    limit: int,
) -> list[int]:
    pages: list[int] = []
    seen: set[int] = set()
    for chunk in chunks:
        page = int(chunk["source_page"])
        if page in seen:
            continue
        seen.add(page)
        pages.append(page)
        if len(pages) == limit:
            break
    return pages


def compare_strategies(
    truth: dict[str, Any],
    paper_directory: Path,
    embedding_model: EmbeddingModel | None = None,
) -> dict[str, Any]:
    """Compare existing chunk retrievers against the locked page-search baseline."""
    paths = check_papers(truth, paper_directory)
    baseline = run(truth, paper_directory)
    cached_model = _CachedEmbeddingModel(
        embedding_model
        or E5EmbeddingModel(
            local_files_only=True,
            revision=EVALUATION_MODEL_REVISION,
        )
    )
    candidates: dict[str, list[dict[str, Any]]] = {
        "semantic": [],
        "hybrid": [],
    }

    with TemporaryDirectory(prefix="research-copilot-m8-4b-") as temporary:
        chunks_by_alias: dict[str, list[dict[str, int | str]]] = {}
        for alias, path in paths.items():
            page_data_path = Path(temporary) / f"{alias}.json"
            import_pdf_to_json(path, page_data_path)
            pages = load_page_data(page_data_path)["pages"]
            chunks_by_alias[alias] = chunk_pages(pages)

        limit = int(truth["per_paper_limit"])
        candidate_pool = max(limit * 8, 20)
        for case in truth["cases"]:
            for strategy in candidates:
                paper_results: dict[str, dict[str, Any]] = {}
                for alias, chunks in chunks_by_alias.items():
                    if strategy == "semantic":
                        ranked = semantic_search_chunks(
                            case["query"], chunks, cached_model, limit=candidate_pool
                        )
                    else:
                        ranked = hybrid_search_chunks(
                            case["query"], chunks, cached_model, limit=candidate_pool
                        )
                    paper_results[alias] = {
                        "paper_id": alias,
                        "status": "matched" if ranked else "no_match" if chunks else "unsearchable",
                        "hits": [
                            {"paper_id": alias, "source_page": page}
                            for page in _top_distinct_pages(ranked, limit)
                        ],
                    }
                candidates[strategy].append(score_case(case, paper_results))

    check_papers(truth, paper_directory)
    return {
        "dataset_id": truth["dataset_id"],
        "per_paper_limit": truth["per_paper_limit"],
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "embedding_revision": EVALUATION_MODEL_REVISION,
        "chunk_size": 1000,
        "chunk_overlap": 100,
        "strategies": {
            "page_keyword": {
                "metrics": baseline["metrics"],
                "cases": baseline["cases"],
            },
            **{
                strategy: {"metrics": summarize(cases), "cases": cases}
                for strategy, cases in candidates.items()
            },
        },
    }


def _page_level_rrf(
    first: list[dict[str, int | float | str]],
    second: list[dict[str, int | float | str]],
    limit: int,
) -> list[int]:
    scores: dict[int, float] = {}
    for ranked in (first, second):
        for rank, page in enumerate(
            _top_distinct_pages(ranked, len(ranked)), start=1
        ):
            scores[page] = scores.get(page, 0.0) + 1.0 / (60 + rank)
    return [
        page
        for page, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[
            :limit
        ]
    ]


def _is_short_term_query(query: str) -> bool:
    if re.search(r"[\u3400-\u9fff?？]", query):
        return False
    return len(re.findall(r"[A-Za-z0-9-]+", query)) <= 3


def _normalized_phrase(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9-]+", text.casefold()))


def _score_gate_cases(
    prepared: list[dict[str, Any]],
    threshold: float | None,
) -> list[dict[str, Any]]:
    scored_cases: list[dict[str, Any]] = []
    for prepared_case in prepared:
        case = prepared_case["truth"]
        paper_results: dict[str, dict[str, Any]] = {}
        for alias, candidate in prepared_case["papers"].items():
            accepted = True
            if threshold is not None:
                accepted = (
                    candidate["exact_phrase_match"]
                    if candidate["gate_kind"] == "exact_phrase"
                    else candidate["max_semantic_similarity"] >= threshold
                )
            pages = candidate["pages"] if accepted else []
            paper_results[alias] = {
                "paper_id": alias,
                "status": "matched" if pages else "no_match",
                "hits": [
                    {"paper_id": alias, "source_page": page} for page in pages
                ],
            }
        scored = score_case(case, paper_results)
        for alias, candidate in prepared_case["papers"].items():
            scored["papers"][alias].update(
                {
                    "gate_kind": candidate["gate_kind"],
                    "exact_phrase_match": candidate["exact_phrase_match"],
                    "max_semantic_similarity": candidate[
                        "max_semantic_similarity"
                    ],
                }
            )
        scored_cases.append(scored)
    return scored_cases


def evaluate_evidence_gate(
    truth: dict[str, Any],
    paper_directory: Path,
    embedding_model: EmbeddingModel | None = None,
    thresholds: tuple[float, ...] = EVIDENCE_GATE_THRESHOLDS,
) -> dict[str, Any]:
    """Evaluate page-level fusion and an explicit evidence admission gate."""
    paths = check_papers(truth, paper_directory)
    cached_model = _CachedEmbeddingModel(
        embedding_model
        or E5EmbeddingModel(
            local_files_only=True,
            revision=EVALUATION_MODEL_REVISION,
        )
    )
    prepared: list[dict[str, Any]] = []

    with TemporaryDirectory(prefix="research-copilot-m8-4c-") as temporary:
        chunks_by_alias: dict[str, list[dict[str, int | str]]] = {}
        for alias, path in paths.items():
            page_data_path = Path(temporary) / f"{alias}.json"
            import_pdf_to_json(path, page_data_path)
            pages = load_page_data(page_data_path)["pages"]
            chunks_by_alias[alias] = chunk_pages(pages)

        limit = int(truth["per_paper_limit"])
        candidate_pool = max(limit * 8, 20)
        for case in truth["cases"]:
            prepared_case: dict[str, Any] = {"truth": case, "papers": {}}
            short_term = _is_short_term_query(case["query"])
            query_phrase = _normalized_phrase(case["query"])
            for alias, chunks in chunks_by_alias.items():
                semantic = semantic_search_chunks(
                    case["query"], chunks, cached_model, limit=candidate_pool
                )
                hybrid = hybrid_search_chunks(
                    case["query"], chunks, cached_model, limit=candidate_pool
                )
                keyword = search_chunks(
                    case["query"], chunks, limit=candidate_pool
                )
                pages = (
                    _page_level_rrf(semantic, hybrid, limit)
                    if keyword
                    else _top_distinct_pages(hybrid, limit)
                )
                normalized_corpus = _normalized_phrase(
                    " ".join(str(chunk["text"]) for chunk in chunks)
                )
                prepared_case["papers"][alias] = {
                    "pages": pages,
                    "gate_kind": "exact_phrase" if short_term else "cosine",
                    "exact_phrase_match": bool(
                        query_phrase and query_phrase in normalized_corpus
                    ),
                    "max_semantic_similarity": max(
                        (float(result["score"]) for result in semantic),
                        default=-1.0,
                    ),
                }
            prepared.append(prepared_case)

    natural_positive_scores: list[float] = []
    natural_negative_scores: list[float] = []
    for prepared_case in prepared:
        for alias, candidate in prepared_case["papers"].items():
            if candidate["gate_kind"] != "cosine":
                continue
            expected_pages = prepared_case["truth"]["relevant_pages"][alias]
            target = (
                natural_positive_scores if expected_pages else natural_negative_scores
            )
            target.append(candidate["max_semantic_similarity"])

    positive_floor = min(natural_positive_scores)
    negative_ceiling = max(natural_negative_scores)
    negative_rejecting_threshold = math.nextafter(negative_ceiling, math.inf)
    scanned_thresholds = sorted(
        set((*thresholds, positive_floor, negative_rejecting_threshold))
    )
    sweep = []
    for threshold in scanned_thresholds:
        cases = _score_gate_cases(prepared, threshold)
        sweep.append(
            {
                "threshold": threshold,
                "metrics": summarize(cases),
                "cases": cases,
            }
        )

    ungated_cases = _score_gate_cases(prepared, None)
    check_papers(truth, paper_directory)
    return {
        "dataset_id": truth["dataset_id"],
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "embedding_revision": EVALUATION_MODEL_REVISION,
        "natural_positive_min_similarity": positive_floor,
        "natural_negative_max_similarity": negative_ceiling,
        "single_cosine_threshold_separable": positive_floor > negative_ceiling,
        "ungated_page_fusion": {
            "metrics": summarize(ungated_cases),
            "cases": ungated_cases,
        },
        "threshold_sweep": sweep,
    }


def _choose_calibration_threshold(
    prepared: list[dict[str, Any]],
) -> dict[str, float | bool]:
    positive_scores: list[float] = []
    negative_scores: list[float] = []
    for prepared_case in prepared:
        if prepared_case["truth"].get("split") != "calibration":
            continue
        for alias, candidate in prepared_case["papers"].items():
            expected_pages = prepared_case["truth"]["relevant_pages"][alias]
            target = positive_scores if expected_pages else negative_scores
            target.append(candidate["evidence_sufficiency_score"])
    if not positive_scores or not negative_scores:
        raise ValueError("Calibration split requires positive and negative pairs.")

    positive_floor = min(positive_scores)
    negative_ceiling = max(negative_scores)
    return {
        "threshold": positive_floor,
        "positive_floor": positive_floor,
        "negative_ceiling": negative_ceiling,
        "separable": positive_floor > negative_ceiling,
    }


def _score_sufficiency_cases(
    prepared: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
    scored_cases: list[dict[str, Any]] = []
    for prepared_case in prepared:
        case = prepared_case["truth"]
        paper_results: dict[str, dict[str, Any]] = {}
        for alias, candidate in prepared_case["papers"].items():
            accepted = candidate["evidence_sufficiency_score"] >= threshold
            pages = candidate["pages"] if accepted else []
            paper_results[alias] = {
                "paper_id": alias,
                "status": "matched" if pages else "no_match",
                "hits": [
                    {"paper_id": alias, "source_page": page} for page in pages
                ],
            }
        scored = score_case(case, paper_results)
        scored["split"] = case["split"]
        for alias, candidate in prepared_case["papers"].items():
            scored["papers"][alias]["evidence_sufficiency_score"] = candidate[
                "evidence_sufficiency_score"
            ]
        scored_cases.append(scored)
    return scored_cases


def evaluate_fine_grained_evidence(
    truth: dict[str, Any],
    paper_directory: Path,
    embedding_model: EmbeddingModel | None = None,
    relevance_model: FineGrainedRelevanceModel | None = None,
) -> dict[str, Any]:
    """Calibrate token alignment on old questions and evaluate held-out questions."""
    paths = check_papers(truth, paper_directory)
    cached_model = _CachedEmbeddingModel(
        embedding_model
        or E5EmbeddingModel(
            local_files_only=True,
            revision=EVALUATION_MODEL_REVISION,
        )
    )
    pair_scorer = relevance_model or E5TokenAlignmentModel(
        local_files_only=True,
        revision=EVALUATION_MODEL_REVISION,
    )
    prepared: list[dict[str, Any]] = []

    with TemporaryDirectory(prefix="research-copilot-m8-4d-") as temporary:
        chunks_by_alias: dict[str, list[dict[str, int | str]]] = {}
        for alias, path in paths.items():
            page_data_path = Path(temporary) / f"{alias}.json"
            import_pdf_to_json(path, page_data_path)
            pages = load_page_data(page_data_path)["pages"]
            chunks_by_alias[alias] = chunk_pages(pages)

        limit = int(truth["per_paper_limit"])
        candidate_pool = max(limit * 8, 20)
        for case in truth["cases"]:
            if case.get("split") not in {"calibration", "held_out"}:
                raise ValueError(f"{case['id']} 缺少有效的评测 split。")
            prepared_case: dict[str, Any] = {"truth": case, "papers": {}}
            for alias, chunks in chunks_by_alias.items():
                semantic = semantic_search_chunks(
                    case["query"], chunks, cached_model, limit=candidate_pool
                )
                hybrid = hybrid_search_chunks(
                    case["query"], chunks, cached_model, limit=candidate_pool
                )
                keyword = search_chunks(
                    case["query"], chunks, limit=candidate_pool
                )
                pages = (
                    _page_level_rrf(semantic, hybrid, limit)
                    if keyword
                    else _top_distinct_pages(hybrid, limit)
                )
                candidate_chunks = [
                    chunk for chunk in chunks if int(chunk["source_page"]) in pages
                ]
                pair_scores = pair_scorer.score_pairs(
                    case["query"],
                    [str(chunk["text"]) for chunk in candidate_chunks],
                )
                if len(pair_scores) != len(candidate_chunks):
                    raise ValueError(
                        "Fine-grained score count must match candidate chunk count."
                    )
                prepared_case["papers"][alias] = {
                    "pages": pages,
                    "evidence_sufficiency_score": max(pair_scores, default=-1.0),
                }
            prepared.append(prepared_case)

    calibration = _choose_calibration_threshold(prepared)
    threshold = float(calibration["threshold"])
    scored = _score_sufficiency_cases(prepared, threshold)
    calibration_cases = [case for case in scored if case["split"] == "calibration"]
    held_out_cases = [case for case in scored if case["split"] == "held_out"]
    if not calibration_cases or not held_out_cases:
        raise ValueError("Evaluation requires calibration and held-out cases.")

    check_papers(truth, paper_directory)
    return {
        "dataset_id": truth["dataset_id"],
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "embedding_revision": EVALUATION_MODEL_REVISION,
        "signal": "experimental_e5_token_late_interaction",
        "calibration": {
            **calibration,
            "metrics": summarize(calibration_cases),
            "cases": calibration_cases,
        },
        "held_out": {
            "threshold": threshold,
            "metrics": summarize(held_out_cases),
            "cases": held_out_cases,
        },
    }
