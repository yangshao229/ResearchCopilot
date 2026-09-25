from pathlib import Path

from research_copilot.document_service import PaperDocumentService
from research_copilot.paper_structure import PaperStructure


def test_document_service_reuses_structure_until_pdf_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"first version")
    calls: list[Path] = []

    def fake_extract(path: Path) -> PaperStructure:
        calls.append(path)
        return PaperStructure(
            page_count=len(calls),
            sections=[],
            method="unavailable",
        )

    monkeypatch.setattr(
        "research_copilot.document_service.extract_paper_structure",
        fake_extract,
    )
    service = PaperDocumentService()

    first = service.structure(pdf_path)
    second = service.structure(pdf_path)
    pdf_path.write_bytes(b"second and longer version")
    third = service.structure(pdf_path)

    assert first is second
    assert third.page_count == 2
    assert calls == [pdf_path, pdf_path]
