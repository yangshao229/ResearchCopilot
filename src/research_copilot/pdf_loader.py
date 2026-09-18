from pathlib import Path

from pypdf import PdfReader


def load_pdf_pages(pdf_path: Path) -> list[dict[str, int | str]]:
    reader = PdfReader(pdf_path)
    pages: list[dict[str, int | str]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(
            {
                "source_page": page_number,
                "text": text,
            }
        )

    return pages