from pathlib import Path

import pytest
from pydantic import ValidationError

from research_copilot.domain import Evidence, EvidenceSet, SourceDocumentRef
from research_copilot.paper_answer_service import PaperAnswerService


class StubSearch:
    def __init__(self) -> None:
        self.calls = 0

    def search(self, pdf_path, paper_id, query, mode, limit=5, scope=None):
        self.calls += 1
        return [
            {"source_page": 2, "chunk_index": 3, "text": "Original passage.", "score": 0.8}
        ]


def test_evidence_set_owns_citation_text_order_and_source() -> None:
    source = SourceDocumentRef(
        paper_uid="paper-" + "a" * 32,
        pdf_sha256="b" * 64,
    )
    evidence_set = EvidenceSet(
        query="What is the method?",
        origin="retrieval",
        candidates=[
            Evidence(
                evidence_id=1,
                source_page=2,
                chunk_index=3,
                text="Original passage.",
                score=0.8,
                source=source.at_page(2),
            )
        ],
    )

    citations = evidence_set.citations_for([99, 1, 1])

    assert len(citations) == 1
    assert citations[0].quote == "Original passage."
    assert citations[0].source == source.at_page(2)


def test_evidence_set_rejects_duplicate_or_missing_candidate_ids() -> None:
    item = Evidence(
        evidence_id=1,
        source_page=1,
        chunk_index=0,
        text="Original passage.",
        score=1.0,
    )
    with pytest.raises(ValidationError, match="unique and sequential"):
        EvidenceSet(query="question", origin="retrieval", candidates=[item, item])
    with pytest.raises(ValidationError, match="unique and sequential"):
        EvidenceSet(
            query="question",
            origin="retrieval",
            candidates=[item.model_copy(update={"evidence_id": 2})],
        )


def test_direct_selection_uses_same_bundle_without_searching() -> None:
    search = StubSearch()
    service = PaperAnswerService(search)
    source = SourceDocumentRef(
        paper_uid="paper-" + "a" * 32,
        pdf_sha256="b" * 64,
    )
    selected = {
        "source_page": 4,
        "chunk_index": 0,
        "text": "Only this selected sentence.",
        "score": 1.0,
    }

    selected_set = service.collect_evidence(
        Path("paper.pdf"),
        "paper-id",
        "Translate this selection",
        "hybrid",
        direct_evidence=[selected],
        source_document=source,
    )
    retrieved_set = service.collect_evidence(
        Path("paper.pdf"), "paper-id", "What is the method?", "keyword"
    )

    assert selected_set.origin == "selection"
    assert selected_set.candidates[0].source == source.at_page(4)
    assert selected_set.candidates[0].text == selected["text"]
    assert retrieved_set.origin == "retrieval"
    assert retrieved_set.candidates[0].evidence_id == 1
    assert search.calls == 1


def test_candidate_from_other_pdf_version_is_not_relabelled() -> None:
    service = PaperAnswerService(StubSearch())
    source = SourceDocumentRef(
        paper_uid="paper-" + "a" * 32,
        pdf_sha256="b" * 64,
    )
    stale = source.model_copy(update={"pdf_sha256": "c" * 64}).at_page(4)

    with pytest.raises(ValueError, match="different PDF version"):
        service.collect_evidence(
            Path("paper.pdf"),
            "paper-id",
            "Translate",
            "keyword",
            direct_evidence=[
                {
                    "source_page": 4,
                    "chunk_index": 0,
                    "text": "Old source.",
                    "score": 1.0,
                    "source": stale.model_dump(),
                }
            ],
            source_document=source,
        )
