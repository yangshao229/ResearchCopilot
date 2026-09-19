from pathlib import Path

from research_copilot.page_store import save_page_data
from research_copilot.paper_search import search_page_data


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