from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.domain import LanguagePolicy
from research_copilot.language_preferences import PaperLanguagePreferenceStore
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


def create_test_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as pdf_file:
        writer.write(pdf_file)


def test_language_preferences_are_paper_scoped_and_persistent(
    tmp_path: Path,
) -> None:
    store = PaperLanguagePreferenceStore(tmp_path / "preferences")
    english = LanguagePolicy(
        explanation_language="en",
        translation_target="en",
        terminology_policy="preserve_english",
        source_language_override="zh-CN",
    )

    store.save("paper-a", english)

    assert PaperLanguagePreferenceStore(tmp_path / "preferences").get(
        "paper-a"
    ) == english
    assert store.get("paper-b") == LanguagePolicy()

    legacy_path = tmp_path / "preferences" / "legacy.json"
    legacy_path.write_text(
        '{"explanation_language":"en","translation_target":"zh-CN",'
        '"terminology_policy":"preserve_english"}',
        encoding="utf-8",
    )
    assert store.get("legacy").source_language_override == "auto"


def test_language_preferences_api_isolated_by_paper(tmp_path: Path) -> None:
    papers = tmp_path / "papers"
    papers.mkdir()
    create_test_pdf(papers / "first.pdf")
    create_test_pdf(papers / "second.pdf")
    client = TestClient(
        create_app(
            paper_directory=papers,
            frontend_directory=tmp_path / "missing-frontend",
            history_store=ReadingHistoryStore(tmp_path / "history"),
            language_preference_store=PaperLanguagePreferenceStore(
                tmp_path / "preferences"
            ),
        )
    )
    paper_ids = {
        paper["name"]: paper["id"] for paper in client.get("/api/papers").json()
    }
    first_id = paper_ids["first.pdf"]
    second_id = paper_ids["second.pdf"]
    assert all(
        paper["detected_source_language"] == "unknown"
        for paper in client.get("/api/papers").json()
    )

    response = client.put(
        f"/api/papers/{first_id}/language",
        json={
            "explanation_language": "en",
            "translation_target": "en",
            "terminology_policy": "preserve_english",
            "source_language_override": "en",
        },
    )

    assert response.status_code == 200
    assert client.get(f"/api/papers/{first_id}/language").json() == response.json()
    assert client.get(f"/api/papers/{second_id}/language").json() == {
        "explanation_language": "follow_question",
        "translation_target": "zh-CN",
        "terminology_policy": "bilingual_first_use",
        "source_language_override": "auto",
    }

    invalid = client.put(
        f"/api/papers/{first_id}/language",
        json={"explanation_language": "fr"},
    )
    assert invalid.status_code == 422

    invalid_override = client.put(
        f"/api/papers/{first_id}/language",
        json={"source_language_override": "fr"},
    )
    assert invalid_override.status_code == 422
