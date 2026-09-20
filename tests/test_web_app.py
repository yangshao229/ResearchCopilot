from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.web_app import create_app


def create_test_pdf(path: Path, page_count: int = 2) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)

    with path.open("wb") as pdf_file:
        writer.write(pdf_file)


def test_paper_api_lists_local_pdfs(tmp_path: Path) -> None:
    paper_path = tmp_path / "attention.pdf"
    create_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )

    response = client.get("/api/papers")

    assert response.status_code == 200
    papers = response.json()
    assert len(papers) == 1
    assert papers[0]["name"] == "attention.pdf"
    assert papers[0]["relative_path"] == "attention.pdf"
    assert papers[0]["page_count"] == 2


def test_paper_api_serves_pdf_file(tmp_path: Path) -> None:
    paper_path = tmp_path / "attention.pdf"
    create_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]

    response = client.get(f"/api/papers/{paper_id}/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_paper_api_rejects_unknown_id(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )

    response = client.get("/api/papers/not-a-paper/file")

    assert response.status_code == 404
    assert response.json() == {"detail": "Paper not found."}
