from pathlib import Path

from research_copilot.page_store import load_page_data, save_page_data

def test_save_and_load_page_data_preserves_content(tmp_path: Path) -> None:
    page_data = {
        "source_pdf": "paper.pdf",
        "pages": [
            {"source_page": 1, "text": "第一页内容"},
            {"source_page": 2, "text": "第二页内容"},
        ],
    }
    output_path = tmp_path / "paper.json"

    save_page_data(page_data, output_path)
    loaded_data = load_page_data(output_path)
    
    assert loaded_data == page_data