from pathlib import Path

import pytest

from research_copilot.paper_answer_service import AnswerCitation, PaperAnswer
from research_copilot.reading_history import ReadingHistoryStore


def sample_answer() -> PaperAnswer:
    return PaperAnswer(
        answer="Transformer removes recurrent computation.",
        explanation="This makes more positions available in parallel.",
        citations=[
            AnswerCitation(
                evidence_id=1,
                source_page=2,
                quote="The Transformer allows for significantly more parallelization.",
            )
        ],
        insufficient_evidence=False,
        uncertainty="The excerpt does not quantify every architecture.",
        evidence=[],
        provider="fake",
        model="fake-model",
    )


def test_history_survives_store_recreation(tmp_path: Path) -> None:
    store = ReadingHistoryStore(tmp_path)
    created = store.add_record(
        "paper-id",
        "paper.pdf",
        "Why is it parallel?",
        "hybrid",
        sample_answer(),
    )

    reloaded = ReadingHistoryStore(tmp_path).list_records("paper-id")

    assert reloaded[0].id == created.id
    assert reloaded[0].citations[0].source_page == 2
    assert reloaded[0].confirmed is False


def test_confirmed_record_exports_reviewable_markdown(tmp_path: Path) -> None:
    store = ReadingHistoryStore(tmp_path)
    created = store.add_record(
        "paper-id",
        "Attention Is All You Need.pdf",
        "Why is it parallel?",
        "hybrid",
        sample_answer(),
    )

    with pytest.raises(ValueError):
        store.export_record("paper-id", created.id)

    store.update_record(
        "paper-id",
        created.id,
        confirmed=True,
        personal_note="My understanding: no recurrent dependency between positions.",
        category="method",
    )
    output_path = store.export_record("paper-id", created.id)
    markdown = output_path.read_text(encoding="utf-8")

    assert "review_status: confirmed" in markdown
    assert "PDF 第 2 页" in markdown
    assert "My understanding" in markdown
    assert store.list_records("paper-id")[0].category == "method"
