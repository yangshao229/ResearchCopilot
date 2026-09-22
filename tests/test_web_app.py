from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.page_store import save_page_data
from research_copilot.paper_answer_service import (
    AnswerCitation,
    ModelAnswerDraft,
    PaperAnswer,
    PaperAnswerService,
)
from research_copilot.paper_card_compiler import PaperCardCompiler
from research_copilot.paper_search_service import PaperSearchService
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.semantic_retriever import EmbeddingModel
from research_copilot.web_app import create_app


def create_test_pdf(path: Path, page_count: int = 2) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)

    with path.open("wb") as pdf_file:
        writer.write(pdf_file)


def create_bookmarked_test_pdf(path: Path) -> None:
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    introduction = writer.add_outline_item("1 Introduction", 0)
    writer.add_outline_item("1.1 Motivation", 1, parent=introduction)
    writer.add_outline_item("2 Method", 2)
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


def test_paper_api_imports_pdf_from_browser(tmp_path: Path) -> None:
    source_path = tmp_path / "source.pdf"
    paper_directory = tmp_path / "papers"
    create_test_pdf(source_path, page_count=3)
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )

    response = client.post(
        "/api/papers/import",
        content=source_path.read_bytes(),
        headers={
            "Content-Type": "application/pdf",
            "X-PDF-Filename": "new-paper.pdf",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["imported"] is True
    assert result["paper"]["name"] == "new-paper.pdf"
    assert result["paper"]["page_count"] == 3
    assert (paper_directory / "new-paper.pdf").exists()


def test_paper_api_detects_duplicate_pdf_content(tmp_path: Path) -> None:
    source_path = tmp_path / "source.pdf"
    paper_directory = tmp_path / "papers"
    create_test_pdf(source_path)
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    pdf_content = source_path.read_bytes()

    first_response = client.post(
        "/api/papers/import",
        content=pdf_content,
        headers={"X-PDF-Filename": "first.pdf"},
    )
    duplicate_response = client.post(
        "/api/papers/import",
        content=pdf_content,
        headers={"X-PDF-Filename": "duplicate.pdf"},
    )

    assert first_response.json()["imported"] is True
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["imported"] is False
    assert duplicate_response.json()["paper"]["name"] == "first.pdf"
    assert len(list(paper_directory.glob("*.pdf"))) == 1


def test_paper_api_rejects_invalid_pdf_upload(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            paper_directory=tmp_path / "papers",
            frontend_directory=tmp_path / "missing-frontend",
        )
    )

    response = client.post(
        "/api/papers/import",
        content=b"not a pdf",
        headers={"X-PDF-Filename": "broken.pdf"},
    )

    assert response.status_code == 400
    assert "有效的 PDF" in response.json()["detail"]


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


def test_paper_api_exposes_clickable_pdf_structure(tmp_path: Path) -> None:
    paper_path = tmp_path / "attention.pdf"
    create_bookmarked_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]

    response = client.get(f"/api/papers/{paper_id}/structure")

    assert response.status_code == 200
    structure = response.json()
    assert structure["method"] == "bookmarks"
    assert structure["sections"][1] == {
        "title": "1.1 Motivation",
        "level": 2,
        "source_page": 2,
        "source": "bookmark",
        "confidence": "high",
    }


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


def test_paper_api_exposes_hybrid_ranking_explanation(tmp_path: Path) -> None:
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
                {
                    "source_page": 7,
                    "text": "The Transformer enables parallel computation.",
                },
            ],
        },
        processed_directory / f"{paper_id}.json",
    )

    response = client.post(
        f"/api/papers/{paper_id}/search",
        json={"query": "Transformer parallel", "mode": "hybrid", "limit": 2},
    )

    assert response.status_code == 200
    results = response.json()
    assert results[0]["source_page"] == 7
    assert results[0]["keyword_rank"] == 1
    assert results[0]["semantic_rank"] == 1
    assert results[0]["fusion_score"] > 0
    assert results[0]["rerank_score"] == results[0]["score"]


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
            history_store=ReadingHistoryStore(tmp_path / "history"),
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
    assert answer["history_id"]

    history_response = client.get(f"/api/papers/{paper_id}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history[0]["id"] == answer["history_id"]
    assert history[0]["confirmed"] is False

    update_response = client.patch(
        f"/api/papers/{paper_id}/history/{answer['history_id']}",
        json={
            "confirmed": True,
            "personal_note": "我确认了第 2 页原文。",
            "category": "method",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["confirmed"] is True

    export_response = client.get(
        f"/api/papers/{paper_id}/history/{answer['history_id']}/export"
    )
    assert export_response.status_code == 200
    assert "review_status: confirmed" in export_response.text
    assert "我确认了第 2 页原文" in export_response.text


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


def test_paper_answer_api_routes_page_count_without_deepseek(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    paper_path = tmp_path / "attention.pdf"
    create_test_pdf(paper_path, page_count=3)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            processed_directory=tmp_path / "processed",
            frontend_directory=tmp_path / "missing-frontend",
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]

    response = client.post(
        f"/api/papers/{paper_id}/answer",
        json={"query": "这篇论文多少页？", "mode": "hybrid"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["answer"] == "这篇 PDF 一共有 3 页。"
    assert answer["provider"] == "local"
    assert answer["evidence"] == []
    assert answer["history_id"]


def test_paper_answer_api_refuses_unreliable_paragraph_count(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    paper_path = tmp_path / "attention.pdf"
    create_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]

    response = client.post(
        f"/api/papers/{paper_id}/answer",
        json={"query": "这一共有多少个段落？", "mode": "hybrid"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["provider"] == "local"
    assert answer["insufficient_evidence"] is True
    assert answer["evidence"] == []


def test_paper_card_api_previews_and_exports_confirmed_records(
    tmp_path: Path,
) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    create_test_pdf(paper_directory / "attention.pdf")
    history = ReadingHistoryStore(tmp_path / "history")
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
            history_store=history,
            card_compiler=PaperCardCompiler(tmp_path / "cards"),
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    answer = PaperAnswer(
        answer="Verified answer.",
        explanation="Explanation.",
        citations=[
            AnswerCitation(
                evidence_id=1,
                source_page=4,
                quote="Verified source text.",
            )
        ],
        insufficient_evidence=False,
        uncertainty="",
        evidence=[],
        provider="fake",
        model="fake-model",
    )
    first = history.add_record(
        paper_id,
        "attention.pdf",
        "What is the method?",
        "hybrid",
        answer,
    )
    second = history.add_record(
        paper_id,
        "attention.pdf",
        "What is the contribution?",
        "hybrid",
        answer,
    )
    history.update_record(paper_id, first.id, True, "My method.", "method")
    history.update_record(
        paper_id,
        second.id,
        True,
        "My contribution.",
        "contributions",
    )

    preview_response = client.get(f"/api/papers/{paper_id}/card/preview")

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["confirmed_record_count"] == 2
    assert "My method." in preview["markdown"]
    assert "[PDF 第 4 页]" in preview["markdown"]

    export_response = client.post(f"/api/papers/{paper_id}/card/export")
    assert export_response.status_code == 200
    assert "review_status: confirmed" in export_response.text

    second_export = client.post(f"/api/papers/{paper_id}/card/export")
    assert second_export.status_code == 409

    preview_with_existing = client.get(
        f"/api/papers/{paper_id}/card/preview"
    ).json()
    assert preview_with_existing["existing_card"] is True
    assert "--- existing/attention.md" in preview_with_existing["diff"]

    version_export = client.post(
        f"/api/papers/{paper_id}/card/export?new_version=true"
    )
    assert version_export.status_code == 200
