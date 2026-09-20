from __future__ import annotations


def recall_at_k(
    results: list[dict[str, int | float | str]],
    relevant_pages: set[int],
    k: int,
) -> float:
    if not relevant_pages or k <= 0:
        return 0.0

    retrieved_pages = {
        int(result["source_page"])
        for result in results[:k]
    }
    return len(retrieved_pages & relevant_pages) / len(relevant_pages)


def reciprocal_rank(
    results: list[dict[str, int | float | str]],
    relevant_pages: set[int],
) -> float:
    for rank, result in enumerate(results, start=1):
        if int(result["source_page"]) in relevant_pages:
            return 1.0 / rank
    return 0.0
