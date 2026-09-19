from pathlib import Path

import pytest

from research_copilot.page_store import save_page_data
from research_copilot.paper_card import write_paper_card


def test_write_paper_card_creates_reviewable_markdown(
    tmp_path: Path,
) -> None:
    page_data_path = tmp_path / "paper.json"
    output_path = tmp_path / "paper.md"
    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [
                {
                    "source_page": 2,
                    "text": "Attention connects tokens.",
                }
            ],
        },
        page_data_path,
    )

    write_paper_card(page_data_path, output_path)

    markdown = output_path.read_text(encoding="utf-8")
    assert 'status: "draft-needs-human-review"' in markdown
    assert "human_confirmed: false" in markdown
    assert "[[paper.pdf#page=2|Page 2]]" in markdown
    assert "- [ ] Verify key findings against cited pages" in markdown


def test_write_paper_card_refuses_to_overwrite_existing_note(
    tmp_path: Path,
) -> None:
    page_data_path = tmp_path / "paper.json"
    output_path = tmp_path / "paper.md"
    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [],
        },
        page_data_path,
    )
    output_path.write_text("existing note", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_paper_card(page_data_path, output_path)
