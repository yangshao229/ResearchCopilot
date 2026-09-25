from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfWriter

from research_copilot.domain import GlossaryEntry
from research_copilot.paper_glossary import (
    PaperGlossaryStore,
    glossary_signature,
    match_glossary_entries,
)
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


def test_glossary_is_paper_scoped_persistent_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    store = PaperGlossaryStore(tmp_path / "glossary")
    first = store.add_entry("paper-a", "  Attention   Head ", "注意力头", "zh-CN")
    store.add_entry("paper-a", "Attention Head", "attention head", "en")

    assert first.source == "Attention Head"
    assert len(PaperGlossaryStore(tmp_path / "glossary").list_entries("paper-a")) == 2
    assert store.list_entries("paper-b") == []
    with pytest.raises(ValueError, match="已有此术语"):
        store.add_entry("paper-a", "attention head", "另一个译名", "zh-CN")
    with pytest.raises(ValueError, match="不能为空"):
        store.add_entry("paper-a", "  ", "错误", "zh-CN")
    with pytest.raises(ValidationError):
        store.add_entry("paper-a", "a" * 101, "过长", "zh-CN")

    store.delete_entry("paper-a", first.id)
    assert len(store.list_entries("paper-a")) == 1
    with pytest.raises(KeyError):
        store.delete_entry("paper-a", first.id)


def test_glossary_matches_exact_words_and_prioritizes_selected_phrases() -> None:
    entries = [
        GlossaryEntry(
            id=str(index),
            source=source,
            translation=f"译名 {index}",
            target_language="zh-CN",
        )
        for index, source in enumerate(
            ["attention", "attention head", "head", "attend", "layer"]
        )
    ]
    entries.append(
        GlossaryEntry(
            id="english",
            source="attention head",
            translation="attention head",
            target_language="en",
        )
    )

    matches = match_glossary_entries(
        entries,
        "An attention head combines signals.",
        "Attention layers may attend to tokens.",
        "zh-CN",
    )

    assert [entry.source for entry in matches[:3]] == [
        "attention head",
        "attention",
        "head",
    ]
    assert all(entry.target_language == "zh-CN" for entry in matches)
    assert [entry.id for entry in match_glossary_entries(
        entries, "An attention head", "", "en"
    )] == ["english"]
    assert match_glossary_entries(
        entries, "inattention is different", "", "zh-CN"
    ) == []
    assert len(
        match_glossary_entries(
            [
                GlossaryEntry(
                    id=str(index),
                    source=f"term{index}",
                    translation=f"译名{index}",
                    target_language="zh-CN",
                )
                for index in range(12)
            ],
            " ".join(f"term{index}" for index in range(12)),
            "",
            "zh-CN",
        )
    ) == 8


def test_glossary_signature_changes_only_for_matched_term_content() -> None:
    first = GlossaryEntry(
        id="a", source="attention", translation="注意力", target_language="zh-CN"
    )
    same_mapping = first.model_copy(update={"id": "b"})
    changed = first.model_copy(update={"translation": "注意机制"})

    assert glossary_signature([first]) == glossary_signature([same_mapping])
    assert glossary_signature([first]) != glossary_signature([changed])
    assert glossary_signature([]) != glossary_signature([first])


def test_glossary_api_isolated_by_paper_and_handles_invalid_entries(
    tmp_path: Path,
) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    for name in ("first.pdf", "second.pdf"):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with (paper_directory / name).open("wb") as output:
            writer.write(output)
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    papers = {paper["name"]: paper["id"] for paper in client.get("/api/papers").json()}
    first_id, second_id = papers["first.pdf"], papers["second.pdf"]

    created = client.post(
        f"/api/papers/{first_id}/glossary",
        json={"source": "attention", "translation": "注意力", "target_language": "zh-CN"},
    )
    assert created.status_code == 200
    assert len(client.get(f"/api/papers/{first_id}/glossary").json()) == 1
    assert client.get(f"/api/papers/{second_id}/glossary").json() == []
    assert client.post(
        f"/api/papers/{first_id}/glossary",
        json={"source": "Attention", "translation": "重复", "target_language": "zh-CN"},
    ).status_code == 409
    assert client.post(
        f"/api/papers/{first_id}/glossary",
        json={"source": " ", "translation": "错误"},
    ).status_code == 422
    assert client.get("/api/papers/missing/glossary").status_code == 404

    assert client.delete(
        f"/api/papers/{first_id}/glossary/{created.json()['id']}"
    ).status_code == 200
    assert client.get(f"/api/papers/{first_id}/glossary").json() == []
