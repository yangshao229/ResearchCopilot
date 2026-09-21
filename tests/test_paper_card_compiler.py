from pathlib import Path

import pytest

from research_copilot.paper_answer_service import AnswerCitation
from research_copilot.paper_card_compiler import PaperCardCompiler
from research_copilot.reading_history import ReadingRecord


def record(
    record_id: str,
    category: str,
    question: str,
    note: str,
    page: int,
    confirmed: bool = True,
) -> ReadingRecord:
    return ReadingRecord.model_validate(
        {
            "id": record_id,
            "paper_id": "paper-id",
            "paper_name": "paper.pdf",
            "created_at": "2026-09-21T00:00:00+00:00",
            "question": question,
            "search_mode": "hybrid",
            "answer": f"AI answer for {question}",
            "explanation": "Explanation",
            "citations": [
                AnswerCitation(
                    evidence_id=1,
                    source_page=page,
                    quote=f"Original evidence on page {page}.",
                )
            ],
            "insufficient_evidence": False,
            "uncertainty": "",
            "provider": "fake",
            "model": "fake-model",
            "confirmed": confirmed,
            "personal_note": note,
            "category": category,
        }
    )


def test_card_requires_two_confirmed_records(tmp_path: Path) -> None:
    compiler = PaperCardCompiler(tmp_path)

    with pytest.raises(ValueError):
        compiler.preview(
            "paper-id",
            "paper.pdf",
            [record("one", "method", "How?", "My method note.", 4)],
        )


def test_card_groups_confirmed_records_and_preserves_citations(
    tmp_path: Path,
) -> None:
    compiler = PaperCardCompiler(tmp_path)
    records = [
        record("method-record", "method", "How does it work?", "My method.", 4),
        record(
            "limit-record",
            "limitations",
            "What is missing?",
            "My limitation.",
            9,
        ),
        record(
            "draft-record",
            "contributions",
            "Unconfirmed",
            "Must not appear.",
            2,
            confirmed=False,
        ),
    ]

    preview = compiler.preview("paper-id", "paper.pdf", records)

    assert preview.confirmed_record_count == 2
    assert preview.existing_card is False
    assert preview.diff == ""
    assert "## 方法" in preview.markdown
    assert "My method." in preview.markdown
    assert "[PDF 第 4 页]" in preview.markdown
    assert "## 局限" in preview.markdown
    assert "My limitation." in preview.markdown
    assert "Must not appear." not in preview.markdown
    assert "## 实验\n\n> TODO" in preview.markdown


def test_export_refuses_to_overwrite_existing_card(tmp_path: Path) -> None:
    compiler = PaperCardCompiler(tmp_path)
    records = [
        record("one", "summary", "Summary?", "Summary.", 1),
        record("two", "method", "Method?", "Method.", 4),
    ]

    output_path = compiler.export("paper-id", "paper.pdf", records)

    assert output_path.read_text(encoding="utf-8").startswith("---")
    with pytest.raises(FileExistsError):
        compiler.export("paper-id", "paper.pdf", records)

    updated_records = [
        record("one", "summary", "Summary?", "Updated summary.", 1),
        record("two", "method", "Method?", "Method.", 4),
    ]
    preview = compiler.preview("paper-id", "paper.pdf", updated_records)
    assert preview.existing_card is True
    assert "--- existing/paper.md" in preview.diff
    assert "+Updated summary." in preview.diff

    version_path = compiler.export(
        "paper-id",
        "paper.pdf",
        updated_records,
        new_version=True,
    )
    assert version_path != output_path
    assert output_path.read_text(encoding="utf-8") != version_path.read_text(
        encoding="utf-8"
    )
