from research_copilot.retrieval_benchmark import evaluate_retrieval_strategies


def test_evaluate_compares_strategies_with_fixed_questions() -> None:
    questions = [
        {
            "id": "parallel",
            "question": "Why can this run in parallel?",
            "relevant_pages": [2],
        }
    ]
    strategies = {
        "baseline": lambda query: [
            {
                "source_page": 9,
                "chunk_index": 0,
                "text": "unrelated",
                "score": 1.0,
            },
            {
                "source_page": 2,
                "chunk_index": 0,
                "text": query,
                "score": 0.5,
            },
        ]
    }

    report = evaluate_retrieval_strategies(questions, strategies, limit=2)

    baseline = report["strategies"]["baseline"]
    assert baseline["mean_recall_at_k"] == 1.0
    assert baseline["mean_reciprocal_rank"] == 0.5
    assert baseline["cases"][0]["retrieved_pages"] == [9, 2]
