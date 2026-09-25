from pathlib import Path

from research_copilot.page_store import save_page_data
from research_copilot.domain import ReadingScope
from research_copilot.paper_search import (
    search_page_data,
    semantic_search_page_data,
)
from research_copilot.semantic_retriever import EmbeddingModel


def test_search_page_data_returns_ranked_page_citations(
    tmp_path: Path,
) -> None:
    page_data_path = tmp_path / "paper.json"

    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [
                {
                    "source_page": 1,
                    "text": "Attention connects tokens.",
                },
                {
                    "source_page": 2,
                    "text": "Attention uses attention weights.",
                },
                {
                    "source_page": 3,
                    "text": "Convolution processes images.",
                },
            ],
        },
        page_data_path,
    )

    results = search_page_data(
        page_data_path,
        "attention",
        chunk_size=100,
        overlap=0,
        limit=2,
    )

    assert [
        (result["source_page"], result["score"])
        for result in results
    ] == [
        (2, 2),
        (1, 1),
    ]


def test_search_page_data_filters_pages_to_resolved_section(
    tmp_path: Path,
) -> None:
    page_data_path = tmp_path / "paper.json"
    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [
                {"source_page": 1, "text": "shared term from introduction"},
                {"source_page": 2, "text": "shared term from method"},
                {"source_page": 3, "text": "shared term from results"},
            ],
        },
        page_data_path,
    )

    results = search_page_data(
        page_data_path,
        "shared term",
        chunk_size=100,
        overlap=0,
        limit=5,
        scope=ReadingScope(
            kind="section",
            resolution="matched",
            section_title="2 Method",
            start_page=2,
            end_page=2,
        ),
    )

    assert results
    assert {result["source_page"] for result in results} == {2}


class PageAwareFakeEmbeddingModel(EmbeddingModel):
    def embed_query(self, query: str) -> list[float]:
        return [1.0, 0.0]

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        return [[0.1, 0.9], [0.8, 0.2]]


def test_semantic_search_page_data_preserves_page_citations(
    tmp_path: Path,
) -> None:
    page_data_path = tmp_path / "paper.json"
    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [
                {"source_page": 3, "text": "First passage."},
                {"source_page": 7, "text": "Second passage."},
            ],
        },
        page_data_path,
    )

    results = semantic_search_page_data(
        page_data_path,
        "中文问题",
        chunk_size=100,
        overlap=0,
        limit=1,
        embedding_model=PageAwareFakeEmbeddingModel(),
    )

    assert results[0]["source_page"] == 7
