"""Deterministic scoring for the local M8.4a real-paper benchmark."""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from research_copilot.hybrid_retriever import hybrid_search_chunks
from research_copilot.library_organization import LibraryOrganizationStore
from research_copilot.page_store import load_page_data
from research_copilot.pdf_importer import import_pdf_to_json
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.semantic_retriever import (
    DEFAULT_EMBEDDING_MODEL,
    E5EmbeddingModel,
    EmbeddingModel,
    semantic_search_chunks,
)
from research_copilot.text_splitter import chunk_pages
from research_copilot.web_app import create_app


EVALUATION_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


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


class _CachedEmbeddingModel:
    def __init__(self, model: EmbeddingModel) -> None:
        self.model = model
        self.query_cache: dict[str, list[float]] = {}
        self.passage_cache: dict[tuple[str, ...], list[list[float]]] = {}

    def embed_query(self, query: str) -> list[float]:
        if query not in self.query_cache:
            self.query_cache[query] = self.model.embed_query(query)
        return self.query_cache[query]

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        key = tuple(passages)
        if key not in self.passage_cache:
            self.passage_cache[key] = self.model.embed_passages(passages)
        return self.passage_cache[key]


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
