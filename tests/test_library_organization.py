from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.library_organization import LibraryOrganizationStore
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


def _test_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    with path.open("wb") as output:
        writer.write(output)


def test_collections_and_tags_are_many_to_many_and_persistent(tmp_path: Path) -> None:
    store = LibraryOrganizationStore(tmp_path / "organization")
    methods = store.create_collection(" Methods ")
    project = store.create_collection("Project Alpha")

    first = store.save_paper(
        "paper-a",
        [methods.id, project.id, methods.id],
        ["Transformer", " transformer ", "To Read"],
    )
    store.save_paper("paper-b", [methods.id], ["Survey"])

    assert first.collection_ids == [methods.id, project.id]
    assert first.tags == ["Transformer", "To Read"]
    reloaded = LibraryOrganizationStore(tmp_path / "organization")
    assert reloaded.get_paper("paper-a") == first
    assert reloaded.get_paper("paper-b").tags == ["Survey"]


def test_invalid_updates_do_not_overwrite_existing_organization(
    tmp_path: Path,
) -> None:
    store = LibraryOrganizationStore(tmp_path / "organization")
    collection = store.create_collection("Reading queue")
    expected = store.save_paper("paper-a", [collection.id], ["To Read"])

    with pytest.raises(ValueError, match="不存在"):
        store.save_paper("paper-a", ["missing"], ["Changed"])
    assert store.get_paper("paper-a") == expected

    with pytest.raises(ValueError, match="同名"):
        store.create_collection(" reading   QUEUE ")
    with pytest.raises(ValueError, match="40"):
        store.save_paper("paper-a", [collection.id], ["x" * 41])
    assert store.get_paper("paper-a") == expected


def test_deleting_collection_only_unlinks_papers(tmp_path: Path) -> None:
    store = LibraryOrganizationStore(tmp_path / "organization")
    keep = store.create_collection("Keep")
    remove = store.create_collection("Remove")
    store.save_paper("paper-a", [keep.id, remove.id], ["Important"])

    store.delete_collection(remove.id)

    assert [item.id for item in store.list_collections()] == [keep.id]
    assert store.get_paper("paper-a").collection_ids == [keep.id]
    assert store.get_paper("paper-a").tags == ["Important"]
    with pytest.raises(KeyError):
        store.delete_collection("missing")


def test_library_organization_api_keeps_papers_separate(tmp_path: Path) -> None:
    papers = tmp_path / "papers"
    papers.mkdir()
    _test_pdf(papers / "first.pdf")
    _test_pdf(papers / "second.pdf")
    organization = LibraryOrganizationStore(tmp_path / "organization")
    client = TestClient(
        create_app(
            paper_directory=papers,
            frontend_directory=tmp_path / "web",
            history_store=ReadingHistoryStore(tmp_path / "history"),
            library_organization_store=organization,
        )
    )
    paper_ids = {
        item["name"]: item["id"] for item in client.get("/api/papers").json()
    }

    created = client.post(
        "/api/library/collections", json={"name": "Core papers"}
    )
    assert created.status_code == 200
    collection_id = created.json()["id"]
    duplicate = client.post(
        "/api/library/collections", json={"name": " core PAPERS "}
    )
    assert duplicate.status_code == 409

    saved = client.put(
        f"/api/papers/{paper_ids['first.pdf']}/organization",
        json={"collection_ids": [collection_id], "tags": ["Method", "method"]},
    )
    assert saved.status_code == 200
    assert saved.json() == {
        "collection_ids": [collection_id],
        "tags": ["Method"],
    }

    listed = {item["name"]: item for item in client.get("/api/papers").json()}
    assert listed["first.pdf"]["collection_ids"] == [collection_id]
    assert listed["first.pdf"]["tags"] == ["Method"]
    assert listed["second.pdf"]["collection_ids"] == []
    assert listed["second.pdf"]["tags"] == []

    invalid = client.put(
        f"/api/papers/{paper_ids['first.pdf']}/organization",
        json={"collection_ids": ["missing"], "tags": ["Changed"]},
    )
    assert invalid.status_code == 409
    assert client.get("/api/papers/missing/organization").status_code == 404

    removed = client.delete(f"/api/library/collections/{collection_id}")
    assert removed.status_code == 200
    assert (papers / "first.pdf").exists()
    remaining = client.get(
        f"/api/papers/{paper_ids['first.pdf']}/organization"
    ).json()
    assert remaining == {"collection_ids": [], "tags": ["Method"]}
