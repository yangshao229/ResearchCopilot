import json
from pathlib import Path

import pytest

from research_copilot.paper_identity import PaperIdentityStore


def test_identity_survives_path_change_when_pdf_bytes_match(tmp_path: Path) -> None:
    store = PaperIdentityStore(tmp_path / "identities")
    digest = "a" * 64

    original = store.resolve(
        legacy_paper_id="old-id",
        relative_path="old/paper.pdf",
        pdf_sha256=digest,
    )
    moved = store.resolve(
        legacy_paper_id="new-id",
        relative_path="renamed/paper.pdf",
        pdf_sha256=digest,
    )

    assert moved.paper_uid == original.paper_uid
    assert moved.version_status == "current"
    saved = json.loads((tmp_path / "identities" / "index.json").read_text())
    assert saved[0]["legacy_paper_ids"] == ["old-id", "new-id"]
    assert saved[0]["relative_paths"] == [
        "old/paper.pdf",
        "renamed/paper.pdf",
    ]


def test_identity_flags_changed_bytes_without_silently_accepting_version(
    tmp_path: Path,
) -> None:
    store = PaperIdentityStore(tmp_path / "identities")
    original = store.resolve(
        legacy_paper_id="paper-id",
        relative_path="paper.pdf",
        pdf_sha256="a" * 64,
    )

    changed = store.resolve(
        legacy_paper_id="paper-id",
        relative_path="paper.pdf",
        pdf_sha256="b" * 64,
    )

    assert changed.paper_uid == original.paper_uid
    assert changed.version_status == "changed"
    assert changed.registered_pdf_sha256 == "a" * 64
    assert changed.pdf_sha256 == "b" * 64
    saved = json.loads((tmp_path / "identities" / "index.json").read_text())
    assert saved[0]["pdf_sha256"] == "a" * 64


def test_identity_index_fails_closed_on_duplicate_alias(tmp_path: Path) -> None:
    index_path = tmp_path / "identities" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            [
                {
                    "paper_uid": f"paper-{'1' * 32}",
                    "pdf_sha256": "a" * 64,
                    "legacy_paper_ids": ["same-id"],
                    "relative_paths": ["one.pdf"],
                },
                {
                    "paper_uid": f"paper-{'2' * 32}",
                    "pdf_sha256": "b" * 64,
                    "legacy_paper_ids": ["same-id"],
                    "relative_paths": ["two.pdf"],
                },
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate legacy paper ID"):
        PaperIdentityStore(index_path.parent).resolve(
            legacy_paper_id="same-id",
            relative_path="one.pdf",
            pdf_sha256="a" * 64,
        )
