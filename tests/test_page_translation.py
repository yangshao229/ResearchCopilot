from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.domain import LanguagePolicy
from research_copilot.language_preferences import PaperLanguagePreferenceStore
from research_copilot.page_translation import (
    MAX_PAGE_TEXT_CHARS,
    DeepSeekPageTranslationModel,
    PageTranslationService,
)
from research_copilot.paper_glossary import PaperGlossaryStore
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


class FakePageSource:
    def __init__(self) -> None:
        self.pages = {1: "Transformer uses attention.", 2: "Training uses Adam."}

    def page_text(self, _pdf_path: Path, _paper_id: str, source_page: int) -> str:
        return self.pages.get(source_page, "")


class FakeTranslationModel:
    provider_name = "fake"
    model_name = "fake-translation-v1"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def translate(self, source_text: str, policy: LanguagePolicy, terms: list) -> str:
        self.calls.append((source_text, policy.translation_target, len(terms)))
        return f"译文 {len(self.calls)}: {source_text}"


def make_service(tmp_path: Path) -> tuple[PageTranslationService, FakePageSource, FakeTranslationModel, PaperGlossaryStore]:
    source = FakePageSource()
    model = FakeTranslationModel()
    glossary = PaperGlossaryStore(tmp_path / "glossary")
    service = PageTranslationService(source, glossary, tmp_path / "translations", model)
    return service, source, model, glossary


def test_page_translation_is_explicit_cached_and_isolated(tmp_path: Path) -> None:
    service, source, model, glossary = make_service(tmp_path)
    policy = LanguagePolicy()
    pdf_path = tmp_path / "paper.pdf"

    assert service.cached(pdf_path, "paper-one", 1, policy) is None
    assert model.calls == []
    first = service.translate(pdf_path, "paper-one", 1, policy)
    assert first.source_page == 1
    assert first.target_language == "zh-CN"
    assert first.cache_hit is False
    assert service.translate(pdf_path, "paper-one", 1, policy).cache_hit is True
    assert len(model.calls) == 1

    service.translate(pdf_path, "paper-one", 2, policy)
    service.translate(pdf_path, "paper-two", 1, policy)
    english = policy.model_copy(update={"translation_target": "en"})
    service.translate(pdf_path, "paper-one", 1, english)
    assert len(model.calls) == 4

    glossary.add_entry("paper-one", "Transformer", "变换器", "zh-CN")
    service.translate(pdf_path, "paper-one", 1, policy)
    assert model.calls[-1] == (source.pages[1], "zh-CN", 1)
    assert len(model.calls) == 5

    source.pages[1] = "Transformer uses cross-attention."
    service.translate(pdf_path, "paper-one", 1, policy)
    assert len(model.calls) == 6
    service.translate(pdf_path, "paper-one", 1, policy, refresh=True)
    assert len(model.calls) == 7

    preserve_english = policy.model_copy(update={"terminology_policy": "preserve_english"})
    service.translate(pdf_path, "paper-one", 1, preserve_english)
    assert len(model.calls) == 8


def test_page_translation_rejects_missing_or_overlong_text(tmp_path: Path) -> None:
    service, source, model, _ = make_service(tmp_path)
    with pytest.raises(ValueError, match="没有可抽取的文字"):
        service.translate(tmp_path / "paper.pdf", "paper-one", 3, LanguagePolicy())
    source.pages[1] = "a" * (MAX_PAGE_TEXT_CHARS + 1)
    with pytest.raises(ValueError, match="过长"):
        service.translate(tmp_path / "paper.pdf", "paper-one", 1, LanguagePolicy())
    assert model.calls == []


def test_page_translation_api_reads_cache_without_model_call(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_path = paper_directory / "paper.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)
    service, _, model, _ = make_service(tmp_path)
    app = create_app(
        paper_directory=paper_directory,
        frontend_directory=tmp_path / "missing-frontend",
        history_store=ReadingHistoryStore(tmp_path / "history"),
        language_preference_store=PaperLanguagePreferenceStore(tmp_path / "language"),
        page_translation_service=service,
    )
    client = TestClient(app)
    paper_id = client.get("/api/papers").json()[0]["id"]
    url = f"/api/papers/{paper_id}/pages/1/translation"

    assert client.get(url).json() is None
    assert model.calls == []
    response = client.post(url, json={"refresh": False})
    assert response.status_code == 200
    assert response.json()["translated_text"].startswith("译文")
    assert client.get(url).json()["cache_hit"] is True
    assert len(model.calls) == 1
    assert client.get(f"/api/papers/{paper_id}/pages/3/translation").status_code == 422
    assert client.post(f"/api/papers/missing/pages/1/translation", json={}).status_code == 404


def test_deepseek_page_translation_sends_only_selected_page_text() -> None:
    requests = []

    class Response:
        status_code = 200

        def json(self) -> dict:
            return {"output_text": '{"translated_text":"这是译文。"}'}

    def post(url: str, **kwargs):
        requests.append((url, kwargs))
        return Response()

    model = DeepSeekPageTranslationModel(api_key="test-key", post=post)
    output = model.translate("Only page one text.", LanguagePolicy(), [])

    assert output == "这是译文。"
    assert len(requests) == 1
    assert "Only page one text." in requests[0][1]["json"]["input"]
    assert "整篇" not in requests[0][1]["json"]["input"]
