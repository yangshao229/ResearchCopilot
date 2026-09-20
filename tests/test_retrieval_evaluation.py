from research_copilot.retrieval_evaluation import (
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k_counts_unique_relevant_pages() -> None:
    results = [
        {"source_page": 4, "chunk_index": 0, "text": "a", "score": 1.0},
        {"source_page": 4, "chunk_index": 1, "text": "b", "score": 0.9},
        {"source_page": 5, "chunk_index": 0, "text": "c", "score": 0.8},
    ]

    assert recall_at_k(results, {4, 5}, 2) == 0.5
    assert recall_at_k(results, {4, 5}, 3) == 1.0


def test_reciprocal_rank_uses_first_relevant_result() -> None:
    results = [
        {"source_page": 10, "chunk_index": 0, "text": "a", "score": 1.0},
        {"source_page": 2, "chunk_index": 0, "text": "b", "score": 0.9},
    ]

    assert reciprocal_rank(results, {2}) == 0.5
    assert reciprocal_rank(results, {7}) == 0.0
