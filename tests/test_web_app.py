from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.conversation_sessions import ConversationSessionStore
from research_copilot.page_store import load_page_data, save_page_data
from research_copilot.paper_answer_service import (
    AnswerCitation,
    ModelAnswerDraft,
    PaperAnswer,
    PaperAnswerService,
)
from research_copilot.paper_card_compiler import PaperCardCompiler
from research_copilot.paper_identity import hash_pdf
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
    assert papers[0]["paper_uid"].startswith("paper-")
    assert len(papers[0]["pdf_sha256"]) == 64
    assert papers[0]["pdf_version_status"] == "current"


def test_health_api_exposes_frontend_contract_version(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            paper_directory=tmp_path / "papers",
            frontend_directory=tmp_path / "missing-frontend",
        )
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "api_schema": 2,
    }


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


def test_paper_api_builds_reading_guide_from_real_outline(tmp_path: Path) -> None:
    paper_path = tmp_path / "attention.pdf"
    create_bookmarked_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]

    response = client.get(f"/api/papers/{paper_id}/guide")

    assert response.status_code == 200
    guide = response.json()
    assert guide["method"] == "structure:bookmarks"
    assert any("1 Introduction" in item["label"] for item in guide["questions"])
    assert any("2 Method" in item["label"] for item in guide["questions"])


def test_paper_api_creates_isolated_conversation_sessions(tmp_path: Path) -> None:
    create_test_pdf(tmp_path / "first.pdf")
    create_test_pdf(tmp_path / "second.pdf", page_count=3)
    client = TestClient(
        create_app(
            paper_directory=tmp_path,
            frontend_directory=tmp_path / "missing-frontend",
            session_store=ConversationSessionStore(tmp_path / "sessions"),
        )
    )
    papers = client.get("/api/papers").json()
    first_id = next(paper["id"] for paper in papers if paper["name"] == "first.pdf")
    second_id = next(paper["id"] for paper in papers if paper["name"] == "second.pdf")

    created_response = client.post(
        f"/api/papers/{first_id}/sessions",
        json={"title": "方法精读"},
    )

    assert created_response.status_code == 200
    created = created_response.json()
    assert created["paper_id"] == first_id
    assert created["title"] == "方法精读"
    first_sessions = client.get(f"/api/papers/{first_id}/sessions").json()
    second_sessions = client.get(f"/api/papers/{second_id}/sessions").json()
    assert [session["title"] for session in first_sessions] == [
        "默认阅读",
        "方法精读",
    ]
    assert [session["title"] for session in second_sessions] == ["默认阅读"]


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
            "source_pdf_sha256": hash_pdf(paper_path),
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
    paper = client.get("/api/papers").json()[0]
    assert results[0]["source"] == {
        "paper_uid": paper["paper_uid"],
        "pdf_sha256": paper["pdf_sha256"],
        "source_page": 2,
    }


def test_legacy_page_cache_without_fingerprint_is_rebuilt_before_source_anchor(
    tmp_path: Path,
) -> None:
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
                {
                    "source_page": 1,
                    "text": "Attention uses a legacy extraction cache.",
                }
            ],
        },
        processed_directory / f"{paper_id}.json",
    )

    response = client.post(
        f"/api/papers/{paper_id}/search",
        json={"query": "legacy", "mode": "keyword", "limit": 3},
    )

    assert response.status_code == 200
    assert response.json() == []
    rebuilt = load_page_data(processed_directory / f"{paper_id}.json")
    assert rebuilt["source_pdf_sha256"] == hash_pdf(paper_path)


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
            "source_pdf_sha256": hash_pdf(paper_path),
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


def test_missing_embedding_model_fails_fast_without_network(
    tmp_path: Path, monkeypatch,
) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    create_test_pdf(paper_directory / "paper.pdf")
    requested_local_only: list[bool] = []

    def unavailable_model(*, local_files_only: bool):
        requested_local_only.append(local_files_only)
        raise OSError("model files are not cached")

    monkeypatch.setattr(
        "research_copilot.paper_search_service.E5EmbeddingModel", unavailable_model
    )
    search_service = PaperSearchService(tmp_path / "processed")
    client = TestClient(create_app(
        paper_directory=paper_directory,
        frontend_directory=tmp_path / "missing-frontend",
        search_service=search_service,
        answer_service=PaperAnswerService(search_service, AnswerApiFakeModel()),
        history_store=ReadingHistoryStore(tmp_path / "history"),
    ))
    paper_id = client.get("/api/papers").json()[0]["id"]

    for endpoint in ("search", "answer"):
        response = client.post(
            f"/api/papers/{paper_id}/{endpoint}",
            json={"query": "What does this paper propose?", "mode": "hybrid"},
        )
        assert response.status_code == 503
        assert "关键词检索" in response.json()["detail"]
    assert requested_local_only == [True, True]


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
            "source_pdf_sha256": hash_pdf(paper_path),
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

    def __init__(self) -> None:
        self.call_count = 0
        self.insufficient_evidence = False
        self.received_glossary_terms = []

    def generate(
        self, question, evidence, language=None, task="question", task_context="",
        glossary_terms=None,
    ):
        self.call_count += 1
        self.received_glossary_terms = glossary_terms or []
        return ModelAnswerDraft(
            answer="Transformer 不使用循环结构，因此能并行处理序列位置。",
            explanation="证据明确对比了循环网络的顺序计算限制。",
            cited_evidence_ids=[1],
            insufficient_evidence=self.insufficient_evidence,
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
            "source_pdf_sha256": hash_pdf(paper_path),
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
        json={
            "query": "Transformer",
            "mode": "keyword",
            "language": {
                "explanation_language": "en",
                "translation_target": "en",
                "terminology_policy": "preserve_english",
            },
        },
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["citations"][0]["source_page"] == 2
    assert answer["provider"] == "fake"
    assert answer["evidence"][0]["source_page"] == 2
    assert answer["history_id"]
    assert answer["language"]["explanation_language"] == "en"

    history_response = client.get(f"/api/papers/{paper_id}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history[0]["id"] == answer["history_id"]
    assert history[0]["confirmed"] is False
    assert history[0]["language"]["translation_target"] == "en"

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


def test_selection_context_preview_and_translation_keep_anchor_and_context(
    tmp_path: Path,
) -> None:
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    paper_path = paper_directory / "attention.pdf"
    create_test_pdf(paper_path, page_count=2)
    search_service = PaperSearchService(processed_directory)
    history_store = ReadingHistoryStore(tmp_path / "history")
    fake_model = AnswerApiFakeModel()
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            processed_directory=processed_directory,
            frontend_directory=tmp_path / "missing-frontend",
            search_service=search_service,
            answer_service=PaperAnswerService(
                search_service,
                fake_model,
            ),
            history_store=history_store,
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    processed_directory.mkdir()
    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "source_pdf_sha256": hash_pdf(paper_path),
            "pages": [
                {
                    "source_page": 1,
                    "text": "Other page content.",
                },
                {
                    "source_page": 2,
                    "text": (
                        "Earlier discussion provides context. " * 60
                        + "The selected clause improves contextual translation. "
                        + "Later discussion explains the consequences. " * 60
                    ),
                },
            ],
        },
        processed_directory / f"{paper_id}.json",
    )
    selected_text = "improves contextual translation."
    preview_response = client.post(
        f"/api/papers/{paper_id}/selection-context",
        json={"source_page": 2, "selected_text": selected_text},
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["method"] == "page_window"
    assert selected_text in preview["context_text"]
    assert client.get(f"/api/papers/{paper_id}/history").json() == []

    answer_response = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "mode": "hybrid",
            "session_id": "default",
            "task": "translate",
            "anchor": {
                "source_page": 2,
                "selected_text": selected_text,
                "section_title": "",
            },
            "language": {
                "explanation_language": "follow_question",
                "translation_target": "zh-CN",
                "terminology_policy": "bilingual_first_use",
            },
        },
    )

    assert answer_response.status_code == 200
    answer = answer_response.json()
    assert answer["citations"][0]["source_page"] == 2
    record = client.get(f"/api/papers/{paper_id}/history").json()[0]
    paper = client.get("/api/papers").json()[0]
    expected_source = {
        "paper_uid": paper["paper_uid"],
        "pdf_sha256": paper["pdf_sha256"],
        "source_page": 2,
    }
    assert answer["citations"][0]["source"] == expected_source
    assert answer["evidence"][0]["source"] == expected_source
    assert record["citations"][0]["source"] == expected_source
    assert record["task"] == "translate"
    assert record["anchor"]["source_page"] == 2
    assert selected_text in record["anchor"]["selected_text"]
    assert selected_text in record["context_text"]
    assert record["prompt_version"] == "selection-translation-v2-glossary"
    assert answer["cache_hit"] is False
    assert fake_model.call_count == 1

    repeated = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "session_id": "default",
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
        },
    )
    assert repeated.status_code == 200
    assert repeated.json()["cache_hit"] is True
    assert repeated.json()["history_id"] == answer["history_id"]
    assert repeated.json()["evidence"][0]["source_page"] == 2
    assert repeated.json()["evidence"][0]["source"] == expected_source
    assert fake_model.call_count == 1
    assert len(history_store.list_records(paper_id)) == 1

    corrected_source_language = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
            "language": {"source_language_override": "en"},
        },
    )
    assert corrected_source_language.json()["cache_hit"] is True
    assert fake_model.call_count == 1

    in_english = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
            "language": {"translation_target": "en"},
        },
    )
    assert in_english.status_code == 200
    assert in_english.json()["cache_hit"] is False
    assert fake_model.call_count == 2

    new_session = client.post(
        f"/api/papers/{paper_id}/sessions", json={"title": "二次精读"}
    ).json()
    other_session = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "session_id": new_session["id"],
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
        },
    )
    assert other_session.json()["cache_hit"] is False
    assert fake_model.call_count == 3

    fake_model.model_name = "new-fake-answer-model"
    other_model = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
        },
    )
    assert other_model.json()["cache_hit"] is False
    assert fake_model.call_count == 4

    refreshed = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
            "refresh_translation": True,
        },
    )
    assert refreshed.json()["cache_hit"] is False
    assert refreshed.json()["history_id"] != other_model.json()["history_id"]
    assert fake_model.call_count == 5

    other_page = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "task": "translate",
            "anchor": {"source_page": 1, "selected_text": "Other page content."},
        },
    )
    assert other_page.json()["cache_hit"] is False
    assert fake_model.call_count == 6

    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "pages": [
                {"source_page": 1, "text": "Other page content."},
                {
                    "source_page": 2,
                    "text": (
                        "Changed context before the selection. " * 60
                        + "The selected clause improves contextual translation. "
                        + "Changed context after the selection. " * 60
                    ),
                },
            ],
        },
        processed_directory / f"{paper_id}.json",
    )
    changed_context = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
        },
    )
    assert changed_context.json()["cache_hit"] is False
    assert fake_model.call_count == 7

    fake_model.insufficient_evidence = True
    failed_request = {
        "query": "翻译当前选中的论文原文",
        "task": "translate",
        "anchor": {"source_page": 2, "selected_text": "New untranslated clause."},
    }
    first_failure = client.post(
        f"/api/papers/{paper_id}/answer", json=failed_request
    )
    second_failure = client.post(
        f"/api/papers/{paper_id}/answer", json=failed_request
    )
    assert first_failure.json()["insufficient_evidence"] is True
    assert "Transformer 不使用循环结构" not in first_failure.json()["answer"]
    failed_record = next(
        record for record in history_store.list_records(paper_id)
        if record.id == first_failure.json()["history_id"]
    )
    assert "Transformer 不使用循环结构" not in failed_record.answer
    assert failed_record.citations == []
    assert second_failure.json()["cache_hit"] is False
    assert fake_model.call_count == 9

    fake_model.insufficient_evidence = False
    current_record = next(
        record
        for record in history_store.list_records(paper_id)
        if record.id == changed_context.json()["history_id"]
    )
    history_store.add_record(
        paper_id,
        "attention.pdf",
        "翻译当前选中的论文原文",
        "hybrid",
        PaperAnswer.model_validate(changed_context.json()),
        session_id=new_session["id"],
        anchor=current_record.anchor,
        context_text=current_record.context_text,
    )
    old_format_record = client.post(
        f"/api/papers/{paper_id}/answer",
        json={
            "query": "翻译当前选中的论文原文",
            "session_id": new_session["id"],
            "task": "translate",
            "anchor": {"source_page": 2, "selected_text": selected_text},
        },
    )
    assert old_format_record.json()["cache_hit"] is False
    assert fake_model.call_count == 10


def test_glossary_preview_model_and_translation_cache_stay_in_sync(
    tmp_path: Path,
) -> None:
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    create_test_pdf(paper_directory / "attention.pdf")
    search_service = PaperSearchService(processed_directory)
    fake_model = AnswerApiFakeModel()
    history_store = ReadingHistoryStore(tmp_path / "history")
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            processed_directory=processed_directory,
            frontend_directory=tmp_path / "missing-frontend",
            search_service=search_service,
            answer_service=PaperAnswerService(search_service, fake_model),
            history_store=history_store,
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    processed_directory.mkdir()
    save_page_data(
        {
            "source_pdf": "attention.pdf",
            "pages": [
                {"source_page": 1, "text": "Other discussion."},
                {
                    "source_page": 2,
                    "text": "An attention head combines representations.",
                },
            ],
        },
        processed_directory / f"{paper_id}.json",
    )
    matched_entry = client.post(
        f"/api/papers/{paper_id}/glossary",
        json={"source": "attention head", "translation": "注意力头"},
    ).json()
    preview_request = {
        "source_page": 2,
        "selected_text": "attention head",
        "target_language": "zh-CN",
    }
    preview = client.post(
        f"/api/papers/{paper_id}/selection-context",
        json=preview_request,
    ).json()
    assert [item["translation"] for item in preview["glossary_terms"]] == [
        "注意力头"
    ]
    assert client.post(
        f"/api/papers/{paper_id}/selection-context",
        json={**preview_request, "target_language": "en"},
    ).json()["glossary_terms"] == []
    assert fake_model.call_count == 0

    answer_request = {
        "query": "翻译当前选中的论文原文",
        "task": "translate",
        "anchor": {"source_page": 2, "selected_text": "attention head"},
    }
    first = client.post(f"/api/papers/{paper_id}/answer", json=answer_request)
    assert first.status_code == 200
    assert [item.translation for item in fake_model.received_glossary_terms] == [
        "注意力头"
    ]
    record = history_store.list_records(paper_id)[0]
    assert record.glossary_signature
    assert client.post(
        f"/api/papers/{paper_id}/answer", json=answer_request
    ).json()["cache_hit"] is True
    assert fake_model.call_count == 1

    client.post(
        f"/api/papers/{paper_id}/glossary",
        json={"source": "unrelated term", "translation": "无关术语"},
    )
    assert client.post(
        f"/api/papers/{paper_id}/answer", json=answer_request
    ).json()["cache_hit"] is True
    assert fake_model.call_count == 1

    assert client.delete(
        f"/api/papers/{paper_id}/glossary/{matched_entry['id']}"
    ).status_code == 200
    after_deletion = client.post(
        f"/api/papers/{paper_id}/answer", json=answer_request
    )
    assert after_deletion.json()["cache_hit"] is False
    assert fake_model.received_glossary_terms == []
    assert fake_model.call_count == 2

    client.post(
        f"/api/papers/{paper_id}/glossary",
        json={"source": "attention head", "translation": "注意机制头"},
    )
    after_change = client.post(
        f"/api/papers/{paper_id}/answer", json=answer_request
    )
    assert after_change.json()["cache_hit"] is False
    assert [item.translation for item in fake_model.received_glossary_terms] == [
        "注意机制头"
    ]
    assert fake_model.call_count == 3


def test_translation_request_requires_a_source_anchor(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    paper_path = paper_directory / "attention.pdf"
    create_test_pdf(paper_path)
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]

    response = client.post(
        f"/api/papers/{paper_id}/answer",
        json={"query": "translate", "task": "translate"},
    )

    assert response.status_code == 422

    non_translation_refresh = client.post(
        f"/api/papers/{paper_id}/answer",
        json={"query": "Summarize the method", "refresh_translation": True},
    )
    assert non_translation_refresh.status_code == 422


def test_paper_answer_and_history_stay_inside_selected_session(
    tmp_path: Path,
) -> None:
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    first_path = paper_directory / "first.pdf"
    second_path = paper_directory / "second.pdf"
    create_test_pdf(first_path)
    create_test_pdf(second_path, page_count=3)
    search_service = PaperSearchService(processed_directory)
    history_store = ReadingHistoryStore(tmp_path / "history")
    session_store = ConversationSessionStore(tmp_path / "sessions")
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
            search_service=search_service,
            answer_service=PaperAnswerService(
                search_service,
                AnswerApiFakeModel(),
            ),
            history_store=history_store,
            session_store=session_store,
        )
    )
    papers = client.get("/api/papers").json()
    first_id = next(paper["id"] for paper in papers if paper["name"] == "first.pdf")
    second_id = next(paper["id"] for paper in papers if paper["name"] == "second.pdf")
    processed_directory.mkdir()
    for paper_id, paper_name in ((first_id, "first.pdf"), (second_id, "second.pdf")):
        save_page_data(
            {
                "source_pdf": paper_name,
                "pages": [{"source_page": 1, "text": "Transformer evidence."}],
            },
            processed_directory / f"{paper_id}.json",
        )
    method_session = client.post(
        f"/api/papers/{first_id}/sessions",
        json={"title": "方法精读"},
    ).json()

    response = client.post(
        f"/api/papers/{first_id}/answer",
        json={
            "query": "Transformer",
            "mode": "keyword",
            "session_id": method_session["id"],
        },
    )

    assert response.status_code == 200
    method_history = client.get(
        f"/api/papers/{first_id}/history",
        params={"session_id": method_session["id"]},
    ).json()
    default_history = client.get(
        f"/api/papers/{first_id}/history",
        params={"session_id": "default"},
    ).json()
    assert len(method_history) == 1
    assert method_history[0]["session_id"] == method_session["id"]
    assert default_history == []

    forged_response = client.post(
        f"/api/papers/{second_id}/answer",
        json={
            "query": "Transformer",
            "mode": "keyword",
            "session_id": method_session["id"],
        },
    )
    assert forged_response.status_code == 404


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
            "source_pdf_sha256": hash_pdf(paper_path),
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
