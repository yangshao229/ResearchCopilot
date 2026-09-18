from pathlib import Path

from pypdf import PdfWriter
from research_copilot.pdf_importer import import_pdf_to_json

from research_copilot.page_store import load_page_data


def test_import_pdf_to_json_preserves_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    output_path = tmp_path / "paper.json"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)
    import_pdf_to_json(pdf_path, output_path)
    page_data = load_page_data(output_path)

    assert page_data == {
        "source_pdf": "paper.pdf",
        "pages": [
            {"source_page": 1, "text": ""},
            {"source_page": 2, "text": ""},
        ],
    }
