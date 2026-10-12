from pathlib import Path

from research_copilot.page_store import save_page_data
from research_copilot.paper_identity import hash_pdf
from research_copilot.pdf_loader import load_pdf_pages


def import_pdf_to_json(pdf_path: Path, output_path: Path) -> None:
    source_fingerprint = hash_pdf(pdf_path)
    pages = load_pdf_pages(pdf_path)
    if hash_pdf(pdf_path) != source_fingerprint:
        raise ValueError("PDF changed during text extraction; please retry.")
    page_data: dict[str, object] = {
        "source_pdf": pdf_path.name,
        "source_pdf_sha256": source_fingerprint,
        "pages": pages,
    }
    save_page_data(page_data, output_path)
