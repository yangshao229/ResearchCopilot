"""Compare answer-bearing context in existing hits and same-page neighbour windows."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from statistics import median
from time import monotonic

from research_copilot.context_window_evaluation import (
    contains_support_on_one_page,
    expand_candidate_neighbours,
    window_text,
)
from research_copilot.hybrid_retriever import hybrid_search_chunks
from research_copilot.pdf_loader import load_pdf_pages
from research_copilot.real_multi_paper_evaluation import check_papers
from research_copilot.reranker_evaluation import rerank_candidates
from research_copilot.semantic_retriever import CachedEmbeddingModel, E5EmbeddingModel
from research_copilot.text_splitter import chunk_pages


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUTH = PROJECT_ROOT / "docs/evaluations/m8_4i_independent_rag_truth.json"
DEFAULT_SUPPORT = PROJECT_ROOT / "docs/evaluations/m8_4j_support_spans.json"
VIEWS = {
    "original": (0, 0),
    "forward": (0, 1),
    "both_sides": (1, 1),
}
EXTENDED_VIEWS = {
    "two_before": (2, 0),
    "two_after": (0, 2),
}
CANDIDATE_NEIGHBOUR_VIEWS = {
    "original": (0, 0),
    "previous": (1, 0),
    "next": (0, 1),
    "both": (1, 1),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--support", type=Path, default=DEFAULT_SUPPORT)
    parser.add_argument("--paper-directory", type=Path, default=PROJECT_ROOT / "data/raw")
    parser.add_argument(
        "--reranker-model", type=Path,
        help="Optional existing local Cross Encoder snapshot; never downloaded.",
    )
    parser.add_argument(
        "--extended-windows", action="store_true",
        help="Also compare two same-page neighbours in each direction.",
    )
    args = parser.parse_args()

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    support = json.loads(args.support.read_text(encoding="utf-8"))
    paths = check_papers(truth, args.paper_directory)
    case_ids = {case["id"] for case in truth["cases"]}
    expected_hashes = {
        alias: paper["sha256"] for alias, paper in truth["papers"].items()
    }
    support_hashes = support.get("paper_sha256_by_alias")
    if support_hashes is None and len(expected_hashes) == 1:
        alias = next(iter(expected_hashes))
        support_hashes = {alias: support.get("paper_sha256")}
    if (
        support["parent_dataset_id"] != truth["dataset_id"]
        or case_ids != set(support["support_markers"])
        or support_hashes != expected_hashes
    ):
        parser.exit(2, "证据真值与 PDF 账本不匹配。\n")

    paper_chunks = {}
    paper_texts = {}
    for alias, paper_path in paths.items():
        pages = load_pdf_pages(paper_path)
        paper_chunks[alias] = chunk_pages(pages)
        paper_texts[alias] = [
            " ".join(str(page["text"]).split()).casefold() for page in pages
        ]
    for case in truth["cases"]:
        if case["paper"] not in paper_chunks:
            parser.exit(2, f"问题引用了未知 PDF：{case['id']}\n")
        markers = support["support_markers"][case["id"]]
        if bool(markers) != bool(case["anchor_pages"]):
            parser.exit(2, f"证据真值的正负标注不匹配：{case['id']}\n")
        normalized_markers = [" ".join(marker.split()).casefold() for marker in markers]
        if any(not marker for marker in normalized_markers):
            parser.exit(2, f"人工证据短语不能为空：{case['id']}\n")
        if markers and not any(
            all(marker in page_text for marker in normalized_markers)
            for page_text in paper_texts[case["paper"]]
        ):
            parser.exit(2, f"人工证据短语未共同出现于同一 PDF 页：{case['id']}\n")

    model = CachedEmbeddingModel(E5EmbeddingModel(local_files_only=True))
    reranker = None
    model_load_seconds = None
    if args.reranker_model is not None:
        if not (args.reranker_model / "model.safetensors").is_file():
            parser.exit(2, f"缺少本地重排序模型：{args.reranker_model}\n")
        from sentence_transformers import CrossEncoder

        started = monotonic()
        reranker = CrossEncoder(
            str(args.reranker_model), device="cpu", local_files_only=True,
            model_kwargs={"use_safetensors": True},
        )
        model_load_seconds = round(monotonic() - started, 3)

    results = []
    view_sizes = {**VIEWS, **EXTENDED_VIEWS} if args.extended_windows else VIEWS
    for case in truth["cases"]:
        chunks = paper_chunks[case["paper"]]
        hits = hybrid_search_chunks(case["query"], chunks, model, limit=5)
        ranked_views = {
            name: (hits, before, after)
            for name, (before, after) in view_sizes.items()
        }
        candidate_support = None
        candidate_anchor_page = None
        rerank_seconds = None
        top_cross_encoder_score = None
        reranked_hits = None
        candidate_variants = None
        if reranker is not None:
            candidates = hybrid_search_chunks(
                case["query"], chunks, model, limit=30,
            )
            candidate_support = contains_support_on_one_page(
                candidates,
                [str(hit["text"]) for hit in candidates],
                support["support_markers"][case["id"]],
            )
            candidate_anchor_page = any(
                int(hit["source_page"]) in case["anchor_pages"]
                for hit in candidates
            ) if case["anchor_pages"] else None
            started = monotonic()
            reranked_hits = rerank_candidates(case["query"], candidates, reranker)[:5]
            rerank_seconds = round(monotonic() - started, 3)
            top_cross_encoder_score = (
                float(reranked_hits[0]["cross_encoder_score"])
                if reranked_hits else None
            )
            ranked_views.update({
                f"reranked_{name}": (reranked_hits, before, after)
                for name, (before, after) in view_sizes.items()
            })
            candidate_variants = {}
            for name, (before, after) in CANDIDATE_NEIGHBOUR_VIEWS.items():
                expanded_candidates = expand_candidate_neighbours(
                    candidates, chunks, before=before, after=after,
                )
                if name == "original":
                    variant_hits = reranked_hits
                    variant_seconds = rerank_seconds
                else:
                    variant_started = monotonic()
                    variant_hits = rerank_candidates(
                        case["query"], expanded_candidates, reranker,
                    )[:5]
                    variant_seconds = round(monotonic() - variant_started, 3)
                markers = support["support_markers"][case["id"]]
                candidate_variants[name] = {
                    "candidate_count": len(expanded_candidates),
                    "candidate_support_spans_present": contains_support_on_one_page(
                        expanded_candidates,
                        [str(hit["text"]) for hit in expanded_candidates],
                        markers,
                    ),
                    "top_5_support_spans_present": contains_support_on_one_page(
                        variant_hits,
                        [str(hit["text"]) for hit in variant_hits],
                        markers,
                    ),
                    "source_pages_at_5": [
                        int(hit["source_page"]) for hit in variant_hits
                    ],
                    "source_chunk_indexes_at_5": [
                        int(hit["chunk_index"]) for hit in variant_hits
                    ],
                    "top_cross_encoder_score": (
                        float(variant_hits[0]["cross_encoder_score"])
                        if variant_hits else None
                    ),
                    "rerank_seconds": variant_seconds,
                }
        views = {}
        for name, (view_hits, before, after) in ranked_views.items():
            texts = [
                window_text(hit, chunks, before=before, after=after)
                for hit in view_hits
            ]
            views[name] = {
                "support_spans_present": contains_support_on_one_page(
                    view_hits, texts, support["support_markers"][case["id"]]
                ),
                "total_characters": sum(len(text) for text in texts),
            }
        results.append({
            "id": case["id"],
            "paper": case["paper"],
            "language": case["language"],
            "kind": "answerable" if case["anchor_pages"] else "no_answer",
            "source_pages_at_5": [int(hit["source_page"]) for hit in hits],
            "source_chunk_indexes_at_5": [int(hit["chunk_index"]) for hit in hits],
            "candidate_support_spans_present": candidate_support,
            "candidate_anchor_page_at_30": candidate_anchor_page,
            "reranked_source_pages_at_5": (
                [int(hit["source_page"]) for hit in reranked_hits]
                if reranked_hits is not None else None
            ),
            "reranked_chunk_indexes_at_5": (
                [int(hit["chunk_index"]) for hit in reranked_hits]
                if reranked_hits is not None else None
            ),
            "top_cross_encoder_score": top_cross_encoder_score,
            "rerank_seconds": rerank_seconds,
            "candidate_variants": candidate_variants,
            "views": views,
        })

    positives = [item for item in results if item["kind"] == "answerable"]
    negatives = [item for item in results if item["kind"] == "no_answer"]
    view_names = tuple(results[0]["views"]) if results else tuple(view_sizes)
    summary = {
        name: {
            "positive_support_at_5": sum(
                item["views"][name]["support_spans_present"] for item in positives
            ),
            "positive_cases": len(positives),
            "mean_total_characters": round(
                sum(item["views"][name]["total_characters"] for item in results)
                / len(results),
            ),
        }
        for name in view_names
    }
    by_paper = {
        alias: {
            name: {
                "positive_support_at_5": sum(
                    item["views"][name]["support_spans_present"]
                    for item in positives if item["paper"] == alias
                ),
                "positive_cases": sum(
                    item["paper"] == alias for item in positives
                ),
            }
            for name in view_names
        }
        for alias in paths
    }
    positive_scores = [
        item["top_cross_encoder_score"] for item in positives
        if item["top_cross_encoder_score"] is not None
    ]
    negative_scores = [
        item["top_cross_encoder_score"] for item in negatives
        if item["top_cross_encoder_score"] is not None
    ]
    candidate_expansion = None
    if reranker is not None:
        candidate_expansion = {}
        for name in CANDIDATE_NEIGHBOUR_VIEWS:
            positive_variants = [item["candidate_variants"][name] for item in positives]
            negative_variants = [item["candidate_variants"][name] for item in negatives]
            variant_positive_scores = [
                item["top_cross_encoder_score"] for item in positive_variants
                if item["top_cross_encoder_score"] is not None
            ]
            variant_negative_scores = [
                item["top_cross_encoder_score"] for item in negative_variants
                if item["top_cross_encoder_score"] is not None
            ]
            candidate_expansion[name] = {
                "positive_candidate_support": sum(
                    item["candidate_support_spans_present"]
                    for item in positive_variants
                ),
                "positive_support_at_5": sum(
                    item["top_5_support_spans_present"]
                    for item in positive_variants
                ),
                "positive_cases": len(positive_variants),
                "mean_candidate_count": round(
                    sum(item["candidate_count"] for item in [
                        *(case["candidate_variants"][name] for case in positives),
                        *(case["candidate_variants"][name] for case in negatives),
                    ]) / len(results),
                ),
                "median_rerank_seconds": median(
                    item["candidate_variants"][name]["rerank_seconds"]
                    for item in results
                ),
                "positive_top_score_min": (
                    min(variant_positive_scores) if variant_positive_scores else None
                ),
                "negative_top_score_max": (
                    max(variant_negative_scores) if variant_negative_scores else None
                ),
                "single_score_threshold_separates": (
                    max(variant_negative_scores) < min(variant_positive_scores)
                    if variant_positive_scores and variant_negative_scores else None
                ),
            }
    print(json.dumps({
        "dataset_id": support["dataset_id"],
        "source_dataset_id": truth["dataset_id"],
        "reranker_revision": args.reranker_model.name if args.reranker_model else None,
        "model_load_seconds": model_load_seconds,
        "summary": summary,
        "by_paper": by_paper,
        "reranker_comparison": {
            "candidate_anchor_page_at_30": sum(
                item["candidate_anchor_page_at_30"] for item in positives
            ),
            "candidate_support_at_30": sum(
                item["candidate_support_spans_present"] for item in positives
            ),
            "gains_at_5": sum(
                not item["views"]["original"]["support_spans_present"]
                and item["views"]["reranked_original"]["support_spans_present"]
                for item in positives
            ),
            "regressions_at_5": sum(
                item["views"]["original"]["support_spans_present"]
                and not item["views"]["reranked_original"]["support_spans_present"]
                for item in positives
            ),
            "median_rerank_seconds": median(
                item["rerank_seconds"] for item in results
            ),
            "positive_top_score_min": min(positive_scores) if positive_scores else None,
            "negative_top_score_max": max(negative_scores) if negative_scores else None,
            "single_score_threshold_separates": (
                max(negative_scores) < min(positive_scores)
                if positive_scores and negative_scores else None
            ),
        } if reranker is not None else None,
        "candidate_expansion": candidate_expansion,
        "cases": results,
        "no_answer_abstention_supported": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
