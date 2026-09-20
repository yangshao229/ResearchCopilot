from __future__ import annotations

from typing import Any, Callable

from research_copilot.retrieval_evaluation import recall_at_k, reciprocal_rank

SearchFunction = Callable[[str], list[dict[str, int | float | str]]]


def evaluate_retrieval_strategies(
    questions: list[dict[str, Any]],
    strategies: dict[str, SearchFunction],
    limit: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {"limit": limit, "strategies": {}}

    for strategy_name, search in strategies.items():
        cases: list[dict[str, Any]] = []
        for question in questions:
            results = search(str(question["question"]))
            relevant_pages = {int(page) for page in question["relevant_pages"]}
            cases.append(
                {
                    "id": question["id"],
                    "retrieved_pages": [
                        int(result["source_page"]) for result in results
                    ],
                    "recall_at_k": recall_at_k(results, relevant_pages, limit),
                    "reciprocal_rank": reciprocal_rank(results, relevant_pages),
                }
            )

        report["strategies"][strategy_name] = {
            "mean_recall_at_k": sum(case["recall_at_k"] for case in cases)
            / len(cases),
            "mean_reciprocal_rank": sum(
                case["reciprocal_rank"] for case in cases
            )
            / len(cases),
            "cases": cases,
        }

    return report
