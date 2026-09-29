from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.domain import LanguagePolicy
from research_copilot.page_quality import inspect_page_text
from research_copilot.paper_glossary import PaperGlossaryStore
from research_copilot.page_translation import PageTranslationService
from research_copilot.web_app import create_app


class FakePageSource:
    def __init__(self, text: str) -> None:
        self.text = text

    def page_text(self, _pdf_path: Path, _paper_id: str, _source_page: int) -> str:
        return self.text


class FakeModel:
    provider_name = "fake"
    model_name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def translate(self, source_text: str, _policy: LanguagePolicy, _terms: list) -> str:
        self.calls += 1
        return source_text


def test_page_quality_distinguishes_obvious_failures_from_normal_text() -> None:
    assert inspect_page_text(1, "  ", 1000).model_dump() == {
        "source_page": 1,
        "extractable_chars": 0,
        "status": "blocked",
        "issues": ["no_text"],
    }
    assert inspect_page_text(2, "Figure 1", 1000).issues == ["short_text"]
    assert inspect_page_text(3, "A " * 100, 1000).status == "ready"
    assert inspect_page_text(4, "A " * 1000, 1000).issues == ["long_text"]
    damaged = inspect_page_text(5, "A" * 100 + "\ufffd" * 4, 1000)
    assert damaged.status == "blocked"
    assert damaged.issues == ["damaged_text"]
    assert inspect_page_text(6, "A" * 100 + "\ufffd", 1000).status == "ready"
    assert inspect_page_text(7, "A" * 100 + " ∈ R", 1000).issues == ["math_review"]


def test_quality_api_is_read_only_and_bad_text_never_reaches_model(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    pdf_path = paper_directory / "paper.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as output:
        writer.write(output)
    source = FakePageSource("A" * 100 + "\ufffd" * 4)
    model = FakeModel()
    service = PageTranslationService(
        source,
        PaperGlossaryStore(tmp_path / "glossary"),
        tmp_path / "translations",
        model,
    )
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
            page_translation_service=service,
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    url = f"/api/papers/{paper_id}/pages/1"

    quality = client.get(f"{url}/quality")
    assert quality.status_code == 200
    assert quality.json()["issues"] == ["damaged_text"]
    assert client.post(f"{url}/translation", json={}).status_code == 422
    assert model.calls == 0
    assert not (tmp_path / "translations").exists()
    assert client.get(f"/api/papers/{paper_id}/pages/2/quality").status_code == 422
    assert client.get("/api/papers/missing/pages/1/quality").status_code == 404

    source.text = "A clearly extractable paper paragraph. " * 5
    assert client.get(f"{url}/quality").json()["status"] == "ready"
    assert client.post(f"{url}/translation", json={}).status_code == 200
    assert model.calls == 1
