from pathlib import Path

from research_copilot.page_store import save_page_data
from research_copilot.pdf_loader import load_pdf_pages


def import_pdf_to_json(pdf_path: Path, output_path: Path) -> None:
    page_data: dict[str, object] = {
        "source_pdf": pdf_path.name,
        "pages": load_pdf_pages(pdf_path),
    }
    save_page_data(page_data, output_path)
