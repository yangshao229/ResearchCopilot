"""Deterministic scoring for the local M8.4a real-paper benchmark."""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from research_copilot.library_organization import LibraryOrganizationStore
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


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
