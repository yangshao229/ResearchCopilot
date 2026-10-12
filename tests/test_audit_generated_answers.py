import json
from pathlib import Path

import pytest

from scripts.audit_generated_answers import load_selection, run, save_audit


def test_frozen_answer_audit_selection_has_eight_distinct_cases() -> None:
    selection, pairs = load_selection()

    assert selection["selection_id"] == "m8.4r-human-answer-audit-v1"
    assert len(pairs) == 8
    assert len({case["id"] for case, _ in pairs}) == 8
    assert {paper["filename"] for _, paper in pairs} == {
        "lora-hu-2021-v2.pdf",
        "sample.pdf",
        "bert-naacl-2019.pdf",
        "rag-lewis-2021-v4.pdf",
    }
    assert sum(bool(case["anchor_pages"]) for case, _ in pairs) == 4


def test_audit_is_saved_privately_and_without_overwriting_stale_temp(tmp_path: Path) -> None:
    output = tmp_path / "audit.json"
    save_audit(output, {"cases": {"first": {"status": "in_progress"}}})
    assert json.loads(output.read_text(encoding="utf-8"))["cases"]["first"]["status"] == "in_progress"
    assert output.stat().st_mode & 0o777 == 0o600

    temporary = tmp_path / ".audit.json.tmp"
    temporary.write_text("unfinished", encoding="utf-8")
    with pytest.raises(FileExistsError):
        save_audit(output, {"cases": {}})
    assert "first" in json.loads(output.read_text(encoding="utf-8"))["cases"]


def test_audit_requires_explicit_bounded_call_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 1 and 8"):
        run(0, tmp_path / "audit.json")
    with pytest.raises(ValueError, match="between 1 and 8"):
        run(9, tmp_path / "audit.json")
