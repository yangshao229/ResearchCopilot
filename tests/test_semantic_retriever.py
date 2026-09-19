from collections.abc import Sequence

from research_copilot.semantic_retriever import semantic_search_chunks


class FakeEmbeddingModel:
    def embed_query(self, query: str) -> list[float]:
        assert query == "为什么不用循环网络？"
        return [1.0, 0.0]

    def embed_passages(self, passages: Sequence[str]) -> list[list[float]]:
        assert list(passages) == [
            "Recurrent networks process tokens sequentially.",
            "Self-attention allows parallel computation.",
        ]
        return [
            [0.2, 0.8],
            [0.9, 0.1],
        ]


def test_semantic_search_ranks_cross_language_meaning() -> None:
    chunks = [
        {
            "source_page": 1,
            "chunk_index": 0,
            "text": "Recurrent networks process tokens sequentially.",
        },
        {
            "source_page": 2,
            "chunk_index": 0,
            "text": "Self-attention allows parallel computation.",
        },
    ]

    results = semantic_search_chunks(
        "为什么不用循环网络？",
        chunks,
        FakeEmbeddingModel(),
        limit=2,
    )

    assert [result["source_page"] for result in results] == [2, 1]
    assert results[0]["score"] == 0.9
