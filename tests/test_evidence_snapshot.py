from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.domain import Evidence, EvidenceSet, SourceDocumentRef
from research_copilot.evidence_snapshot import (
    EvidenceSnapshotKey,
    EvidenceSnapshotStore,
    EvidenceSnapshotUnavailable,
)
from research_copilot.page_store import save_page_data
from research_copilot.paper_answer_service import ModelAnswerDraft, PaperAnswerService
from research_copilot.paper_identity import hash_pdf
from research_copilot.paper_search_service import PaperSearchService
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


def make_pdf(path: Path, pages: int = 2) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as output:
        writer.write(output)


class CountingSearch(PaperSearchService):
    def __init__(self, processed_directory: Path) -> None:
        super().__init__(processed_directory)
        self.calls = 0

    def search(self, *args, **kwargs):
        self.calls += 1
        return super().search(*args, **kwargs)


class CitingModel:
    provider_name = "fake"
    model_name = "fake-citation-model"

    def __init__(self) -> None:
        self.calls = 0
        self.seen_text: list[str] = []

    def generate(
        self, question, evidence, language=None, task="question",
        task_context="", glossary_terms=None,
    ):
        self.calls += 1
        self.seen_text = [item.text for item in evidence]
        return ModelAnswerDraft(
            answer="A cited answer.",
            explanation="From the original passage.",
            cited_evidence_ids=[1],
            insufficient_evidence=False,
            uncertainty="",
        )


def setup_client(tmp_path: Path):
    paper_directory = tmp_path / "papers"
    processed_directory = tmp_path / "processed"
    paper_directory.mkdir()
    processed_directory.mkdir()
    paper_path = paper_directory / "paper.pdf"
    make_pdf(paper_path)
    searcher = CountingSearch(processed_directory)
    model = CitingModel()
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            processed_directory=processed_directory,
            frontend_directory=tmp_path / "no-frontend",
            search_service=searcher,
            answer_service=PaperAnswerService(searcher, model),
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    page_data_path = processed_directory / f"{paper_id}.json"
    save_page_data(
        {
            "source_pdf": paper_path.name,
            "source_pdf_sha256": hash_pdf(paper_path),
            "pages": [{"source_page": 1, "text": "Transformer original passage."}],
        },
        page_data_path,
    )
    return client, paper_path, page_data_path, paper_id, searcher, model


def test_preview_answer_uses_exact_snapshot_not_a_second_search(tmp_path: Path) -> None:
    client, paper_path, page_data_path, paper_id, searcher, model = setup_client(tmp_path)
    request = {"query": "Transformer", "mode": "keyword", "limit": 5}
    preview = client.post(f"/api/papers/{paper_id}/search", json=request)
    token = preview.headers.get("X-Evidence-Snapshot")
    assert preview.status_code == 200 and token
    original = preview.json()[0]["text"]

    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "source_pdf_sha256": hash_pdf(paper_path),
            "pages": [{"source_page": 1, "text": "Transformer changed passage."}],
        },
        page_data_path,
    )
    answer = client.post(
        f"/api/papers/{paper_id}/answer",
        json={**request, "evidence_snapshot": token},
    )

    assert answer.status_code == 200
    assert answer.json()["evidence"][0]["text"] == original
    assert answer.json()["citations"][0]["quote"] == original
    assert model.seen_text == [original]
    assert searcher.calls == 1


def test_snapshot_mismatch_and_changed_pdf_fail_before_model_or_history(tmp_path: Path) -> None:
    client, paper_path, _, paper_id, searcher, model = setup_client(tmp_path)
    request = {"query": "Transformer", "mode": "keyword", "limit": 5}
    preview = client.post(f"/api/papers/{paper_id}/search", json=request)
    token = preview.headers["X-Evidence-Snapshot"]
    assert preview.json()[0]["source"]["pdf_sha256"] == hash_pdf(paper_path)

    for changes in (
        {"query": "Another question"},
        {"mode": "hybrid"},
        {"limit": 4},
        {"scope_preference": "full_paper"},
    ):
        response = client.post(
            f"/api/papers/{paper_id}/answer",
            json={**request, **changes, "evidence_snapshot": token},
        )
        assert response.status_code == 409
        assert "重新检索" in response.json()["detail"]

    restarted_search = CountingSearch(tmp_path / "processed")
    restarted_model = CitingModel()
    restarted_client = TestClient(
        create_app(
            paper_directory=tmp_path / "papers",
            processed_directory=tmp_path / "processed",
            frontend_directory=tmp_path / "no-frontend",
            search_service=restarted_search,
            answer_service=PaperAnswerService(restarted_search, restarted_model),
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    restarted = restarted_client.post(
        f"/api/papers/{paper_id}/answer",
        json={**request, "evidence_snapshot": token},
    )
    assert restarted.status_code == 409
    assert restarted_model.calls == 0

    make_pdf(paper_path, pages=3)
    changed = client.post(
        f"/api/papers/{paper_id}/answer",
        json={**request, "evidence_snapshot": token},
    )
    assert changed.status_code == 409
    assert model.calls == 0
    assert searcher.calls == 1
    assert client.get(f"/api/papers/{paper_id}/history").json() == []


def test_pdf_change_during_generation_does_not_save_stale_answer(tmp_path: Path) -> None:
    client, paper_path, _, paper_id, _, model = setup_client(tmp_path)
    request = {"query": "Transformer", "mode": "keyword", "limit": 5}
    preview = client.post(f"/api/papers/{paper_id}/search", json=request)
    token = preview.headers["X-Evidence-Snapshot"]
    generate = model.generate

    def change_pdf_before_return(*args, **kwargs):
        make_pdf(paper_path, pages=3)
        return generate(*args, **kwargs)

    model.generate = change_pdf_before_return
    answer = client.post(
        f"/api/papers/{paper_id}/answer",
        json={**request, "evidence_snapshot": token},
    )

    assert answer.status_code == 409
    assert model.calls == 1
    assert client.get(f"/api/papers/{paper_id}/history").json() == []


def test_snapshot_store_expiry_eviction_and_scope_isolation() -> None:
    now = [100.0]
    source = SourceDocumentRef(paper_uid="paper-" + "a" * 32, pdf_sha256="b" * 64)
    key = EvidenceSnapshotKey("paper-id", source, "question", "keyword", 5, "auto")
    evidence_set = EvidenceSet(
        query="question",
        origin="retrieval",
        candidates=[
            Evidence(
                evidence_id=1,
                source_page=1,
                chunk_index=0,
                text="Original",
                score=1.0,
                source=source.at_page(1),
            )
        ],
    )
    store = EvidenceSnapshotStore(max_entries=1, ttl_seconds=10, clock=lambda: now[0])
    first = store.issue(key, evidence_set)
    changed_copy = store.resolve(first, key)
    changed_copy.candidates[0].text = "Tampered"
    assert store.resolve(first, key).candidates[0].text == "Original"
    with pytest.raises(EvidenceSnapshotUnavailable):
        store.resolve(
            first,
            EvidenceSnapshotKey("other-paper", source, "question", "keyword", 5, "auto"),
        )
    second = store.issue(key, evidence_set)
    with pytest.raises(EvidenceSnapshotUnavailable):
        store.resolve(first, key)
    now[0] += 10
    with pytest.raises(EvidenceSnapshotUnavailable):
        store.resolve(second, key)


def test_snapshot_store_rejects_unanchored_or_selected_text() -> None:
    source = SourceDocumentRef(paper_uid="paper-" + "a" * 32, pdf_sha256="b" * 64)
    key = EvidenceSnapshotKey("paper-id", source, "question", "keyword", 5, "auto")
    unanchored = Evidence(
        evidence_id=1, source_page=1, chunk_index=0, text="Original", score=1.0
    )
    store = EvidenceSnapshotStore()
    with pytest.raises(ValueError, match="current PDF anchors"):
        store.issue(
            key,
            EvidenceSet(query="question", origin="retrieval", candidates=[unanchored]),
        )
    with pytest.raises(ValueError, match="retrieved evidence"):
        store.issue(
            key,
            EvidenceSet(query="question", origin="selection", candidates=[]),
        )
