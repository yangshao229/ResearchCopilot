import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter

from research_copilot.domain import AnswerCitation, SearchHit, SourceDocumentRef
from research_copilot.page_store import load_page_data, save_page_data
from research_copilot.paper_identity import hash_pdf
from research_copilot.paper_search_service import PaperSearchService


def _blank_pdf(path: Path, page_count: int) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as output:
        writer.write(output)


def test_source_anchor_cannot_disagree_with_evidence_page() -> None:
    source = SourceDocumentRef(
        paper_uid="paper-" + "a" * 32,
        pdf_sha256="b" * 64,
    ).at_page(2)

    with pytest.raises(ValidationError, match="source page"):
        SearchHit(source_page=1, chunk_index=0, text="quote", score=1, source=source)
    with pytest.raises(ValidationError, match="source page"):
        AnswerCitation(evidence_id=1, source_page=1, quote="quote", source=source)


def test_processed_text_rebuilds_when_pdf_changes_without_mtime_change(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    _blank_pdf(pdf_path, 1)
    search = PaperSearchService(tmp_path / "processed")
    assert search.is_page_data_verified(pdf_path, "paper-id")
    original = load_page_data(search.page_data_path("paper-id"))
    original_mtime_ns = pdf_path.stat().st_mtime_ns

    _blank_pdf(pdf_path, 2)
    os.utime(pdf_path, ns=(original_mtime_ns, original_mtime_ns))
    assert search.is_page_data_verified(pdf_path, "paper-id")
    updated = load_page_data(search.page_data_path("paper-id"))

    assert original["source_pdf_sha256"] != updated["source_pdf_sha256"]
    assert updated["source_pdf_sha256"] == hash_pdf(pdf_path)
    assert len(updated["pages"]) == 2


def test_legacy_unfingerprinted_cache_is_rebuilt_before_citing(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    _blank_pdf(pdf_path, 1)
    search = PaperSearchService(tmp_path / "processed")
    search.processed_directory.mkdir()
    save_page_data(
        {"source_pdf": "paper.pdf", "pages": [{"source_page": 1, "text": "stale"}]},
        search.page_data_path("paper-id"),
    )

    assert search.is_page_data_verified(pdf_path, "paper-id")
    rebuilt = load_page_data(search.page_data_path("paper-id"))
    assert rebuilt["source_pdf_sha256"] == hash_pdf(pdf_path)
    assert rebuilt["pages"][0]["text"] == ""
