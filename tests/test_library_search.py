from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.page_store import save_page_data
from research_copilot.paper_identity import hash_pdf
from research_copilot.paper_search_service import PaperSearchService
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


def _blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    with path.open("wb") as output:
        writer.write(output)


def _page_data(path: Path, pdf_path: Path, pages: list[str]) -> None:
    save_page_data(
        {
            "source_pdf": "fixture.pdf",
            "source_pdf_sha256": hash_pdf(pdf_path),
            "pages": [
                {"source_page": number, "text": text}
                for number, text in enumerate(pages, start=1)
            ],
        },
        path,
    )


def test_library_text_search_requires_all_terms_and_preserves_pages(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    _blank_pdf(pdf_path)
    processed = tmp_path / "processed"
    processed.mkdir()
    _page_data(
        processed / "paper-id.json",
        pdf_path,
        [
            "Graph methods appear here without the second term.",
            "Graph attention networks combine neighborhood evidence. " * 8,
        ],
    )

    results, searchable = PaperSearchService(processed).search_library_text(
        pdf_path,
        "paper-id",
        "graph attention",
    )

    assert searchable is True
    assert len(results) == 1
    assert results[0]["source_page"] == 2
    assert results[0]["score"] == 16.0
    assert len(str(results[0]["text"])) <= 282


def test_library_search_api_respects_scope_and_reports_unsearchable_papers(
    tmp_path: Path,
) -> None:
    papers = tmp_path / "papers"
    papers.mkdir()
    _blank_pdf(papers / "first.pdf")
    _blank_pdf(papers / "second.pdf")
    (papers / "broken.pdf").write_bytes(b"not a pdf")
    processed = tmp_path / "processed"
    client = TestClient(
        create_app(
            paper_directory=papers,
            processed_directory=processed,
            frontend_directory=tmp_path / "web",
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    paper_ids = {
        item["name"]: item["id"] for item in client.get("/api/papers").json()
    }
    processed.mkdir()
    _page_data(
        processed / f"{paper_ids['first.pdf']}.json",
        papers / "first.pdf",
        ["Introduction", "Graph attention finds relevant neighbors."],
    )
    _page_data(
        processed / f"{paper_ids['second.pdf']}.json",
        papers / "second.pdf",
        ["Graph convolution uses a different operator."],
    )

    response = client.post(
        "/api/library/search",
        json={
            "query": "graph attention",
            "paper_ids": [
                paper_ids["first.pdf"],
                paper_ids["second.pdf"],
                paper_ids["broken.pdf"],
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_paper_count"] == 3
    assert body["searched_paper_count"] == 2
    assert body["skipped_paper_count"] == 1
    assert body["results"] == [
        {
            "paper_id": paper_ids["first.pdf"],
            "paper_name": "first.pdf",
            "source_page": 2,
            "text": "Graph attention finds relevant neighbors.",
            "score": 2.0,
        }
    ]


def test_library_search_rejects_unknown_scope_and_keeps_empty_scope_empty(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            paper_directory=tmp_path / "papers",
            processed_directory=tmp_path / "processed",
            frontend_directory=tmp_path / "web",
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )

    unknown = client.post(
        "/api/library/search",
        json={"query": "attention", "paper_ids": ["missing"]},
    )
    assert unknown.status_code == 422

    empty = client.post(
        "/api/library/search",
        json={"query": "attention", "paper_ids": []},
    )
    assert empty.status_code == 200
    assert empty.json() == {
        "results": [],
        "requested_paper_count": 0,
        "searched_paper_count": 0,
        "skipped_paper_count": 0,
    }
