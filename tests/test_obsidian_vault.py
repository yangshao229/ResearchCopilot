from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.domain import AnswerCitation, ReadingRecord, SourceDocumentRef
from research_copilot.obsidian_vault import ObsidianVaultStore
from research_copilot.paper_library import DEFAULT_PAPER_DIRECTORY, PaperSummary
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.storage import atomic_write_json
from research_copilot.web_app import DEFAULT_PAPER_IDENTITY_DIRECTORY, create_app


FINGERPRINT = "a" * 64


def test_default_identity_directory_matches_cli_paper_directory() -> None:
    assert DEFAULT_PAPER_IDENTITY_DIRECTORY == (
        DEFAULT_PAPER_DIRECTORY.parent / ".research_copilot" / "paper_identities"
    )


def reviewed_record(paper_id: str = "paper-id", record_id: str = "abc123") -> ReadingRecord:
    return ReadingRecord.model_validate({
        "id": record_id,
        "paper_id": paper_id,
        "paper_name": "paper.pdf",
        "created_at": "2026-10-05T00:00:00+00:00",
        "question": "How does attention work?",
        "session_id": "session-one",
        "search_mode": "hybrid",
        "answer": "Unreviewed model wording must not enter the vault.",
        "explanation": "Model explanation",
        "citations": [AnswerCitation(evidence_id=1, source_page=2, quote="Original PDF quote.")],
        "insufficient_evidence": False,
        "uncertainty": "",
        "provider": "test",
        "model": "test-model",
        "confirmed": True,
        "personal_note": "My verified understanding.",
        "category": "method",
    })


def current_paper(paper_id: str = "paper-id") -> PaperSummary:
    return PaperSummary(
        id=paper_id,
        paper_uid="paper-" + "b" * 32,
        pdf_sha256=FINGERPRINT,
        pdf_version_status="current",
        name="paper.pdf",
        relative_path="paper.pdf",
        page_count=2,
    )


def make_vault(root: Path) -> Path:
    root.mkdir()
    (root / ".obsidian").mkdir()
    (root / "Papers").mkdir()
    (root / "Notes").mkdir()
    return root


def test_vault_connection_is_read_only_and_persists_locally(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    paper = vault / "Papers" / "paper-one.md"
    paper.write_text(
        "---\nschema_version: 1\nkind: paper\nuid: paper-one\n"
        f"title: Example\npdf_sha256: {FINGERPRINT}\n---\n# Example\n",
        encoding="utf-8",
    )
    before = paper.read_bytes()
    store = ObsidianVaultStore(tmp_path / "local" / "vault.json", tmp_path / "cards")

    status = store.connect(str(vault))

    assert status.connected is True
    assert [note.uid for note in status.notes] == ["paper-one"]
    assert paper.read_bytes() == before
    assert ObsidianVaultStore(store.config_path, tmp_path / "cards").status().notes == status.notes
    assert store.disconnect().connected is False
    assert paper.read_bytes() == before


def test_vault_requires_existing_obsidian_folder(tmp_path: Path) -> None:
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    with pytest.raises(ValueError, match="完整路径"):
        store.connect("relative-vault")
    with pytest.raises((OSError, ValueError)):
        store.connect(str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="Obsidian Vault"):
        store.connect(str(tmp_path))
    assert not store.config_path.exists()


def test_vault_reports_invalid_yaml_and_duplicate_uid_without_writing(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    first = vault / "Papers" / "first.md"
    first.write_text(
        "---\nschema_version: 1\nkind: paper\nuid: same\n"
        f"title: First\npdf_sha256: {FINGERPRINT}\n---\n",
        encoding="utf-8",
    )
    duplicate = vault / "Papers" / "second.md"
    duplicate.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
    bad = vault / "Notes" / "broken.md"
    bad.write_text("---\nuid: [\n---\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in (first, duplicate, bad)}

    status = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards").connect(str(vault))

    assert len(status.notes) == 1
    assert len(status.issues) == 2
    assert any("重复" in issue.message for issue in status.issues)
    assert any("YAML" in issue.message for issue in status.issues)
    assert all(path.read_bytes() == content for path, content in before.items())


def test_vault_rejects_boolean_schema_version_and_normalizes_paper_uid(
    tmp_path: Path,
) -> None:
    vault = make_vault(tmp_path / "vault")
    invalid = vault / "Papers" / "boolean-version.md"
    invalid.write_text(
        "---\nschema_version: true\nkind: paper\nuid: paper-invalid\n"
        f"title: Invalid\npdf_sha256: {FINGERPRINT}\n---\n",
        encoding="utf-8",
    )
    note = vault / "Notes" / "confirmed.md"
    note.write_text(
        "---\nschema_version: 1\nkind: reading_note\nuid: note-one\n"
        "paper_uid: '  paper-one  '\nreview_status: confirmed\n---\n",
        encoding="utf-8",
    )

    status = ObsidianVaultStore(
        tmp_path / "config.json", tmp_path / "cards"
    ).connect(str(vault))

    assert [item.uid for item in status.notes] == ["note-one"]
    assert status.notes[0].paper_uid == "paper-one"
    assert len(status.issues) == 1
    assert "v1" in status.issues[0].message


def test_vault_does_not_follow_note_symlink_outside_vault(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    outside = tmp_path / "private.md"
    outside.write_text("private content", encoding="utf-8")
    (vault / "Notes" / "link.md").symlink_to(outside)

    status = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards").connect(str(vault))

    assert status.notes == []
    assert len(status.issues) == 1
    assert "符号链接" in status.issues[0].message
    assert outside.read_text(encoding="utf-8") == "private content"


def test_vault_api_connects_and_disconnects(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    client = TestClient(create_app(
        paper_directory=tmp_path / "papers",
        frontend_directory=tmp_path / "missing-frontend",
        vault_store=ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards"),
    ))

    assert client.get("/api/knowledge/vault").json()["connected"] is False
    assert client.post("/api/knowledge/vault", json={"path": str(vault)}).json()["connected"] is True
    assert client.delete("/api/knowledge/vault").json()["connected"] is False
    assert client.post("/api/knowledge/vault", json={"path": str(tmp_path)}).status_code == 400


def test_reviewed_note_requires_preview_and_never_overwrites(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    (vault / "Notes").rmdir()
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()
    record = reviewed_record()

    preview = store.preview_reading_note(paper, record)
    assert not (vault / "Notes").exists()
    assert preview.relative_path == "Notes/record-abc123.md"
    assert "My verified understanding." in preview.markdown
    assert "Unreviewed model wording" not in preview.markdown
    assert "PDF 第 2 页" in preview.markdown
    assert FINGERPRINT in preview.markdown

    with pytest.raises(ValueError, match="重新预览"):
        store.save_reading_note(paper, record, "0" * 64)
    assert not (vault / "Notes").exists()

    saved = store.save_reading_note(paper, record, preview.sha256)
    target = vault / preview.relative_path
    original = target.read_bytes()
    assert saved.uid == "record-abc123"
    assert store.status().notes[0].paper_uid == paper.paper_uid
    assert original.decode("utf-8") == preview.markdown

    with pytest.raises(FileExistsError, match="不会覆盖"):
        store.save_reading_note(paper, record, preview.sha256)
    assert target.read_bytes() == original


def test_reviewed_note_rejects_changed_source_and_unsafe_vault(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()
    record = reviewed_record()
    original_files = sorted(path.relative_to(vault) for path in vault.rglob("*.md"))

    with pytest.raises(ValueError, match="人工确认"):
        store.preview_reading_note(paper, record.model_copy(update={"confirmed": False}))
    with pytest.raises(ValueError, match="PDF 版本"):
        store.preview_reading_note(
            paper.model_copy(update={"pdf_version_status": "changed"}), record
        )
    with pytest.raises(ValueError, match="原文引用"):
        store.preview_reading_note(paper, record.model_copy(update={"citations": []}))
    with pytest.raises(ValueError, match="当前论文"):
        store.preview_reading_note(paper, record.model_copy(update={"paper_id": "other"}))
    old_source = SourceDocumentRef(
        paper_uid=paper.paper_uid,
        pdf_sha256="c" * 64,
    )
    stale_citation = record.citations[0].model_copy(
        update={"source": old_source.at_page(2)}
    )
    with pytest.raises(ValueError, match="另一版 PDF"):
        store.preview_reading_note(
            paper,
            record.model_copy(update={"citations": [stale_citation]}),
        )
    with pytest.raises(ValueError, match="原始问题"):
        store.preview_reading_note(paper, record.model_copy(update={"question": "  "}))
    assert sorted(path.relative_to(vault) for path in vault.rglob("*.md")) == original_files

    (vault / "Notes").rmdir()
    (vault / "Notes").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="普通文件夹"):
        store.preview_reading_note(paper, record)


def test_preview_is_bound_to_the_connected_vault(tmp_path: Path) -> None:
    first = make_vault(tmp_path / "first-vault")
    second = make_vault(tmp_path / "second-vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    paper = current_paper()
    record = reviewed_record()
    store.connect(str(first))
    preview = store.preview_reading_note(paper, record)

    store.connect(str(second))

    with pytest.raises(ValueError, match="重新预览"):
        store.save_reading_note(paper, record, preview.sha256)
    assert not (first / preview.relative_path).exists()
    assert not (second / preview.relative_path).exists()


def test_invalid_existing_vault_file_blocks_formal_write(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    invalid = vault / "Notes" / "invalid.md"
    invalid.write_text("not a ResearchCopilot note\n", encoding="utf-8")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()
    record = reviewed_record()
    preview = store.preview_reading_note(paper, record)

    with pytest.raises(ValueError, match="未通过校验"):
        store.save_reading_note(paper, record, preview.sha256)
    assert invalid.read_text(encoding="utf-8") == "not a ResearchCopilot note\n"
    assert not (vault / preview.relative_path).exists()


def test_vault_note_api_previews_then_saves_confirmed_record(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=72, height=72)
    with (paper_directory / "paper.pdf").open("wb") as output:
        writer.write(output)
    history = ReadingHistoryStore(tmp_path / "history")
    store = ObsidianVaultStore(tmp_path / "vault-config.json", tmp_path / "cards")
    client = TestClient(create_app(
        paper_directory=paper_directory,
        frontend_directory=tmp_path / "missing-frontend",
        history_store=history,
        vault_store=store,
    ))
    paper_id = client.get("/api/papers").json()[0]["id"]
    record = reviewed_record(paper_id)
    atomic_write_json(
        history.root_directory / f"{paper_id}.json", [record.model_dump(mode="json")]
    )
    client.post("/api/knowledge/vault", json={"path": str(vault)})
    url = f"/api/papers/{paper_id}/history/{record.id}/vault"

    preview_response = client.get(url + "/preview")
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["already_exists"] is False
    assert not (vault / preview["relative_path"]).exists()

    save_response = client.post(url, json={"preview_sha256": preview["sha256"]})
    assert save_response.status_code == 200
    assert save_response.json()["kind"] == "reading_note"
    assert len(client.get("/api/knowledge/vault").json()["notes"]) == 1
    assert client.post(url, json={"preview_sha256": preview["sha256"]}).status_code == 409


def test_paper_card_indexes_only_saved_notes_and_never_overwrites(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()

    with pytest.raises(ValueError, match="至少一条"):
        store.preview_paper_card(paper)

    note_preview = store.preview_reading_note(paper, reviewed_record())
    store.save_reading_note(paper, reviewed_record(), note_preview.sha256)
    card_preview = store.preview_paper_card(paper)
    card_path = vault / card_preview.relative_path
    assert card_preview.relative_path == f"Papers/{paper.paper_uid}.md"
    assert not card_path.exists()
    assert "../Notes/record-abc123.md" in card_preview.markdown
    assert "My verified understanding" not in card_preview.markdown
    assert "Unreviewed model wording" not in card_preview.markdown

    card = store.save_paper_card(paper, card_preview.sha256)
    original = card_path.read_bytes()
    assert card.kind == "paper"
    assert card.paper_uid == paper.paper_uid
    assert len(store.status().notes) == 2
    with pytest.raises(FileExistsError, match="不会覆盖"):
        store.save_paper_card(paper, card_preview.sha256)
    assert card_path.read_bytes() == original


def test_source_catalog_previews_then_creates_base_without_claiming_review(
    tmp_path: Path,
) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()

    preview = store.preview_source_catalog([paper])
    source_path = vault / f"Sources/{paper.paper_uid}.md"
    base_path = vault / "ResearchCopilot 论文库.base"
    assert preview.new_sources == [f"Sources/{paper.paper_uid}.md"]
    assert preview.base_will_create is True
    assert not source_path.exists() and not base_path.exists()

    status = store.save_source_catalog([paper], preview.sha256)
    assert source_path.is_file() and base_path.is_file()
    assert status.notes[0].kind == "paper_source"
    assert status.notes[0].paper_uid == paper.paper_uid
    assert status.notes[0].pdf_sha256 == FINGERPRINT
    assert "kind == \"paper_source\"" in base_path.read_text(encoding="utf-8")
    assert "confirmed" not in source_path.read_text(encoding="utf-8")
    assert not (vault / "Papers" / f"{paper.paper_uid}.md").exists()
    with pytest.raises(ValueError, match="至少一条"):
        store.preview_paper_card(paper)

    source_path.write_text(
        source_path.read_text(encoding="utf-8").replace("reading_status: 待读", "reading_status: 已读")
        + "\nMy own note.\n", encoding="utf-8",
    )
    original_source = source_path.read_bytes()
    original_base = base_path.read_bytes()
    repeated = store.preview_source_catalog([paper])
    assert repeated.new_sources == []
    assert repeated.existing_count == 1
    assert repeated.base_will_create is False
    store.save_source_catalog([paper], repeated.sha256)
    assert source_path.read_bytes() == original_source
    assert base_path.read_bytes() == original_base


def test_source_catalog_rejects_changed_vault_or_pdf(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()
    preview = store.preview_source_catalog([paper])
    (vault / "ResearchCopilot 论文库.base").write_text("views: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="重新预览"):
        store.save_source_catalog([paper], preview.sha256)
    assert not (vault / "Sources").exists()

    with pytest.raises(ValueError, match="PDF 版本"):
        store.preview_source_catalog([paper.model_copy(update={"pdf_version_status": "changed"})])
    (vault / "Sources").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="未通过校验"):
        store.preview_source_catalog([paper])


def test_source_catalog_api_uses_current_library_papers(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with (paper_directory / "paper.pdf").open("wb") as output:
        writer.write(output)
    client = TestClient(create_app(
        paper_directory=paper_directory,
        frontend_directory=tmp_path / "missing-frontend",
        vault_store=ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards"),
    ))
    assert client.get("/api/knowledge/vault/catalog/preview").status_code == 409
    client.post("/api/knowledge/vault", json={"path": str(vault)})
    preview = client.get("/api/knowledge/vault/catalog/preview").json()
    assert len(preview["new_sources"]) == 1
    assert client.post("/api/knowledge/vault/catalog", json={"preview_sha256": "0" * 64}).status_code == 409
    result = client.post("/api/knowledge/vault/catalog", json={"preview_sha256": preview["sha256"]})
    assert result.status_code == 200
    assert [item["kind"] for item in result.json()["notes"]] == ["paper_source"]
    assert client.get("/api/knowledge/vault/catalog/preview").json()["new_sources"] == []


def test_paper_card_preview_expires_on_note_or_vault_change(tmp_path: Path) -> None:
    first = make_vault(tmp_path / "first")
    second = make_vault(tmp_path / "second")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(first))
    paper = current_paper()
    record = reviewed_record()
    note_preview = store.preview_reading_note(paper, record)
    store.save_reading_note(paper, record, note_preview.sha256)
    card_preview = store.preview_paper_card(paper)

    note_path = first / note_preview.relative_path
    note_path.write_text(note_path.read_text(encoding="utf-8") + "\nMy edit.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="重新预览"):
        store.save_paper_card(paper, card_preview.sha256)
    assert not (first / card_preview.relative_path).exists()

    refreshed = store.preview_paper_card(paper)
    store.connect(str(second))
    with pytest.raises((ValueError, FileExistsError)):
        store.save_paper_card(paper, refreshed.sha256)
    assert not (first / card_preview.relative_path).exists()
    assert not (second / card_preview.relative_path).exists()


def test_paper_card_rejects_changed_pdf_and_cross_paper_notes(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    first = current_paper()
    other = current_paper("another-paper").model_copy(
        update={"paper_uid": "paper-" + "c" * 32}
    )
    record = reviewed_record()
    preview = store.preview_reading_note(first, record)
    store.save_reading_note(first, record, preview.sha256)

    with pytest.raises(ValueError, match="至少一条"):
        store.preview_paper_card(other)
    with pytest.raises(ValueError, match="PDF 版本"):
        store.preview_paper_card(first.model_copy(update={"pdf_version_status": "changed"}))


def test_paper_card_api_uses_server_side_vault_notes(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with (paper_directory / "paper.pdf").open("wb") as output:
        writer.write(output)
    history = ReadingHistoryStore(tmp_path / "history")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    client = TestClient(create_app(
        paper_directory=paper_directory,
        frontend_directory=tmp_path / "missing-frontend",
        history_store=history,
        vault_store=store,
    ))
    paper_id = client.get("/api/papers").json()[0]["id"]
    record = reviewed_record(paper_id)
    atomic_write_json(
        history.root_directory / f"{paper_id}.json", [record.model_dump(mode="json")]
    )
    client.post("/api/knowledge/vault", json={"path": str(vault)})
    note_url = f"/api/papers/{paper_id}/history/{record.id}/vault"
    note_preview = client.get(note_url + "/preview").json()
    assert client.post(note_url, json={"preview_sha256": note_preview["sha256"]}).status_code == 200

    card_url = f"/api/papers/{paper_id}/vault/card"
    card_preview = client.get(card_url + "/preview")
    assert card_preview.status_code == 200
    payload = card_preview.json()
    assert payload["already_exists"] is False
    assert client.post(card_url, json={"preview_sha256": payload["sha256"]}).json()["kind"] == "paper"
    assert client.post(card_url, json={"preview_sha256": payload["sha256"]}).status_code == 409

    paper_uid = client.get("/api/papers").json()[0]["paper_uid"]
    document_url = f"/api/papers/{paper_id}/vault/notes/{paper_uid}"
    document = client.get(document_url)
    assert document.status_code == 200
    assert "../Notes/record-abc123.md" in document.json()["markdown"]
    assert client.get(f"/api/papers/{paper_id}/vault/notes/not-found").status_code == 404


def test_vault_readback_uses_current_external_file_without_writing(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()
    record = reviewed_record()
    preview = store.preview_reading_note(paper, record)
    store.save_reading_note(paper, record, preview.sha256)
    note_path = vault / preview.relative_path
    original = note_path.read_bytes()

    first = store.read_document(paper.paper_uid, "record-abc123")
    assert first.markdown.encode("utf-8") == original
    assert note_path.read_bytes() == original

    note_path.write_bytes(original + b"\nAn Obsidian edit.\n")
    second = store.read_document(paper.paper_uid, "record-abc123")
    assert "An Obsidian edit." in second.markdown
    assert second.sha256 != first.sha256
    assert note_path.read_bytes() == original + b"\nAn Obsidian edit.\n"

    with pytest.raises(KeyError):
        store.read_document("paper-" + "c" * 32, "record-abc123")

    note_path.unlink()
    with pytest.raises(KeyError):
        store.read_document(paper.paper_uid, "record-abc123")


def test_vault_readback_rejects_symlink_and_invalid_yaml(tmp_path: Path) -> None:
    vault = make_vault(tmp_path / "vault")
    store = ObsidianVaultStore(tmp_path / "config.json", tmp_path / "cards")
    store.connect(str(vault))
    paper = current_paper()
    record = reviewed_record()
    preview = store.preview_reading_note(paper, record)
    store.save_reading_note(paper, record, preview.sha256)
    note_path = vault / preview.relative_path

    note_path.write_text("broken YAML", encoding="utf-8")
    with pytest.raises(ValueError, match="未通过校验"):
        store.read_document(paper.paper_uid, "record-abc123")

    outside = tmp_path / "outside.md"
    outside.write_text("private content", encoding="utf-8")
    note_path.unlink()
    note_path.symlink_to(outside)
    with pytest.raises(ValueError, match="未通过校验"):
        store.read_document(paper.paper_uid, "record-abc123")
    assert outside.read_text(encoding="utf-8") == "private content"
