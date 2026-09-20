from research_copilot.hybrid_retriever import (
    hybrid_search_chunks,
    reference_penalty,
)
from research_copilot.semantic_retriever import EmbeddingModel


class HybridFakeEmbeddingModel(EmbeddingModel):
    def embed_query(self, query: str) -> list[float]:
        return [1.0, 0.0]

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        return [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.3, 0.7],
        ]


def test_hybrid_search_demotes_reference_list() -> None:
    chunks = [
        {
            "source_page": 10,
            "chunk_index": 0,
            "text": (
                "References\n[1] Transformer arXiv preprint. "
                "[2] Proceedings of Conference. [3] Another paper. "
                "[4] Another paper. [5] Another paper. [6] Another paper."
            ),
        },
        {
            "source_page": 2,
            "chunk_index": 0,
            "text": (
                "Background: recurrent models are sequential. "
                "We propose the Transformer for parallel computation."
            ),
        },
        {
            "source_page": 7,
            "chunk_index": 0,
            "text": "An unrelated training description.",
        },
    ]

    results = hybrid_search_chunks(
        "Why can the Transformer run in parallel?",
        chunks,
        HybridFakeEmbeddingModel(),
        limit=3,
    )

    assert results[0]["source_page"] == 2
    assert float(results[0]["rerank_score"]) > float(
        results[1]["rerank_score"]
    )
    reference_result = next(
        result for result in results if result["source_page"] == 10
    )
    assert float(reference_result["reference_penalty"]) > 0


def test_reference_penalty_ignores_normal_body_citations() -> None:
    text = "We compare attention with recurrent networks [2, 9]."

    assert reference_penalty(text) == 0.0
