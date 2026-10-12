from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_copilot.paper_search import (
    hybrid_search_page_data,
    search_page_data,
    semantic_search_page_data,
)
from research_copilot.retrieval_benchmark import (
    SearchFunction,
    evaluate_retrieval_strategies,
)
from research_copilot.semantic_retriever import E5EmbeddingModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare retrieval strategies on a fixed paper question set."
    )
    parser.add_argument("page_data_path", type=Path)
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("evaluation/retrieval_questions.json"),
    )
    parser.add_argument("--limit", type=int, default=5)
    return parser


def load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as question_file:
        return json.load(question_file)


def main() -> None:
    args = build_parser().parse_args()
    model = E5EmbeddingModel(local_files_only=True)
    strategies: dict[str, SearchFunction] = {
        "keyword": lambda query: search_page_data(
            args.page_data_path,
            query,
            limit=args.limit,
        ),
        "semantic": lambda query: semantic_search_page_data(
            args.page_data_path,
            query,
            limit=args.limit,
            embedding_model=model,
        ),
        "hybrid": lambda query: hybrid_search_page_data(
            args.page_data_path,
            query,
            limit=args.limit,
            embedding_model=model,
        ),
    }
    report = evaluate_retrieval_strategies(
        load_questions(args.questions),
        strategies,
        args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
