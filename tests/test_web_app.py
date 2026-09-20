from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.page_store import save_page_data
from research_copilot.paper_answer_service import (
    ModelAnswerDraft,
    PaperAnswerService,
)
from research_copilot.paper_search_service import PaperSearchService
from research_copilot.semantic_retriever import EmbeddingModel
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


def test_paper_api_searches_current_paper_with_keywords(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    paper_path = paper_directory / "attention.pdf"
    create_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            processed_directory=processed_directory,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    processed_directory.mkdir()
    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "pages": [
                {"source_page": 1, "text": "Convolution processes images."},
                {
                    "source_page": 2,
                    "text": "Attention uses attention weights twice: attention.",
                },
            ],
        },
        processed_directory / f"{paper_id}.json",
    )

    response = client.post(
        f"/api/papers/{paper_id}/search",
        json={"query": "attention", "mode": "keyword", "limit": 3},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["source_page"] == 2
    assert results[0]["score"] == 3.0


class SearchApiFakeEmbeddingModel(EmbeddingModel):
    def embed_query(self, query: str) -> list[float]:
        return [1.0, 0.0]

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        return [[0.1, 0.9], [0.9, 0.1]]


def test_paper_api_searches_current_paper_semantically(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    paper_path = paper_directory / "attention.pdf"
    create_test_pdf(paper_path)
    search_service = PaperSearchService(
        processed_directory,
        embedding_model=SearchApiFakeEmbeddingModel(),
    )
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
            search_service=search_service,
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    processed_directory.mkdir()
    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "pages": [
                {"source_page": 3, "text": "First passage."},
                {"source_page": 7, "text": "Second passage."},
            ],
        },
        processed_directory / f"{paper_id}.json",
    )

    response = client.post(
        f"/api/papers/{paper_id}/search",
        json={"query": "中文问题", "mode": "semantic", "limit": 1},
    )

    assert response.status_code == 200
    results = response.json()
    assert results[0]["source_page"] == 7
    assert results[0]["score"] == 0.9


def test_paper_api_rejects_blank_search_query(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            processed_directory=tmp_path / "processed",
            frontend_directory=tmp_path / "missing-frontend",
        )
    )

    response = client.post(
        "/api/papers/missing/search",
        json={"query": "   ", "mode": "keyword"},
    )

    assert response.status_code == 422


class AnswerApiFakeModel:
    provider_name = "fake"
    model_name = "fake-answer-model"

    def generate(self, question, evidence):
        return ModelAnswerDraft(
            answer="Transformer 不使用循环结构，因此能并行处理序列位置。",
            explanation="证据明确对比了循环网络的顺序计算限制。",
            cited_evidence_ids=[1],
            insufficient_evidence=False,
            uncertainty="证据没有给出完整训练速度比较。",
        )


def test_paper_api_generates_answer_with_verified_page_citation(
    tmp_path: Path,
) -> None:
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    paper_path = paper_directory / "attention.pdf"
    create_test_pdf(paper_path)
    search_service = PaperSearchService(processed_directory)
    answer_service = PaperAnswerService(
        search_service,
        AnswerApiFakeModel(),
    )
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
            search_service=search_service,
            answer_service=answer_service,
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    processed_directory.mkdir()
    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "pages": [
                {
                    "source_page": 2,
                    "text": (
                        "Recurrent models are sequential. "
                        "The Transformer removes recurrence for parallelization."
                    ),
                }
            ],
        },
        processed_directory / f"{paper_id}.json",
    )

    response = client.post(
        f"/api/papers/{paper_id}/answer",
        json={"query": "Transformer", "mode": "keyword"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["citations"][0]["source_page"] == 2
    assert answer["provider"] == "fake"
    assert answer["evidence"][0]["source_page"] == 2


def test_paper_answer_api_explains_missing_deepseek_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    paper_path = tmp_path / "attention.pdf"
    create_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            processed_directory=tmp_path / "processed",
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    processed_directory = tmp_path / "processed"
    processed_directory.mkdir()
    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "pages": [
                {"source_page": 1, "text": "Attention connects positions."}
            ],
        },
        processed_directory / f"{paper_id}.json",
    )

    response = client.post(
        f"/api/papers/{paper_id}/answer",
        json={"query": "attention", "mode": "keyword"},
    )

    assert response.status_code == 503
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]
