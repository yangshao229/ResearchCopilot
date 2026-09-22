import json
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


def test_record_requires_user_note_and_category_before_confirmation(
    tmp_path: Path,
) -> None:
    store = ReadingHistoryStore(tmp_path)
    created = store.add_record(
        "paper-id",
        "paper.pdf",
        "What did I learn?",
        "hybrid",
        sample_answer(),
    )

    with pytest.raises(ValueError, match="个人理解"):
        store.update_record(
            "paper-id",
            created.id,
            confirmed=True,
            personal_note="",
            category="method",
        )

    with pytest.raises(ValueError, match="选择记录所属栏目"):
        store.update_record(
            "paper-id",
            created.id,
            confirmed=True,
            personal_note="My own understanding.",
            category="unclassified",
        )


def test_reading_history_filters_records_by_session(tmp_path: Path) -> None:
    store = ReadingHistoryStore(tmp_path)
    answer = sample_answer()
    store.add_record(
        "paper-id",
        "paper.pdf",
        "Understand the method",
        "hybrid",
        answer,
        session_id="method-session",
    )
    store.add_record(
        "paper-id",
        "paper.pdf",
        "Check the experiments",
        "hybrid",
        answer,
        session_id="experiment-session",
    )

    method_records = store.list_records("paper-id", "method-session")

    assert [record.question for record in method_records] == [
        "Understand the method"
    ]
    assert len(store.list_records("paper-id")) == 2


def test_legacy_record_without_session_is_loaded_into_default_session(
    tmp_path: Path,
) -> None:
    store = ReadingHistoryStore(tmp_path)
    created = store.add_record(
        "paper-id",
        "paper.pdf",
        "Legacy question",
        "hybrid",
        sample_answer(),
    )
    history_path = tmp_path / "paper-id.json"
    raw_records = json.loads(history_path.read_text(encoding="utf-8"))
    raw_records[0].pop("session_id")
    history_path.write_text(
        json.dumps(raw_records, ensure_ascii=False),
        encoding="utf-8",
    )

    reloaded = store.list_records("paper-id", session_id="default")

    assert reloaded[0].id == created.id
    assert reloaded[0].session_id == "default"
