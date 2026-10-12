"""Compare the offline Cross Encoder with the unchanged hybrid ranking."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from research_copilot.page_store import load_page_data
from research_copilot.pdf_importer import import_pdf_to_json
from research_copilot.real_multi_paper_evaluation import check_papers
from research_copilot.reranker_evaluation import evaluate_case, summarize
from research_copilot.semantic_retriever import CachedEmbeddingModel, E5EmbeddingModel
from research_copilot.text_splitter import chunk_pages


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUTH = PROJECT_ROOT / "docs/evaluations/m8_4e_reranker_truth.json"
DEFAULT_MODEL = (
    PROJECT_ROOT
    / "data/model_cache/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1"
    / "snapshots/1427fd652930e4ba29e8149678df786c240d8825"
)
TOP_K = 5
CANDIDATE_LIMIT = 30


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--paper-directory", type=Path, default=PROJECT_ROOT / "data/raw")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()

    # A benchmark must not silently fetch another model revision or upload PDFs.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if not (args.model_path / "model.safetensors").is_file():
        parser.exit(2, f"缺少本地重排序模型：{args.model_path}\n")

    from sentence_transformers import CrossEncoder

    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    paths = check_papers(truth, args.paper_directory)
    embedding_model = CachedEmbeddingModel(E5EmbeddingModel(local_files_only=True))
    start = monotonic()
    model = CrossEncoder(
        str(args.model_path), device="cpu", local_files_only=True,
        model_kwargs={"use_safetensors": True},
    )
    model_load_seconds = round(monotonic() - start, 3)
    with TemporaryDirectory(prefix="research-copilot-reranker-") as temporary:
        chunks_by_paper: dict[str, list[dict[str, int | str]]] = {}
        for alias, path in paths.items():
            page_data_path = Path(temporary) / f"{alias}.json"
            import_pdf_to_json(path, page_data_path)
            chunks_by_paper[alias] = chunk_pages(load_page_data(page_data_path)["pages"])
        results = [
            evaluate_case(
                case,
                chunks_by_paper[case["paper"]],
                embedding_model,
                model,
                top_k=TOP_K,
                candidate_limit=CANDIDATE_LIMIT,
            )
            for case in truth["cases"]
        ]
    positives = [item for item in results if item["kind"] == "answerable"]
    print(json.dumps({
        "dataset_id": truth["dataset_id"],
        "model_revision": args.model_path.name,
        "model_load_seconds": model_load_seconds,
        "top_k": TOP_K,
        "candidate_limit": CANDIDATE_LIMIT,
        "summary": summarize(results),
        "distinct_page_shadow": {
            "anchor_at_5": sum(item["distinct_anchor_at_5"] for item in positives),
            "zh_anchor_at_5": sum(
                item["distinct_anchor_at_5"] for item in positives
                if item["language"] == "zh"
            ),
            "known_irrelevant_at_5": sum(
                item["distinct_known_irrelevant_at_5"] for item in results
            ),
        },
        "cases": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
