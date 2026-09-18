from pathlib import Path

from pypdf import PdfWriter

from research_copilot.pdf_loader import load_pdf_pages


def test_load_pdf_pages_preserves_page_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "two_pages.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    pages = load_pdf_pages(pdf_path)

    assert [page["source_page"] for page in pages] == [1, 2]
    assert [page["text"] for page in pages] == ["", ""]