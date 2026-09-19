import sys
from pathlib import Path

from pypdf import PdfWriter

from research_copilot.cli import main
from research_copilot.page_store import (
    load_page_data,
    save_page_data,
)


def test_import_command_creates_page_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    output_path = tmp_path / "paper.json"

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)

    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research-copilot",
            "import",
            str(pdf_path),
            str(output_path),
        ],
    )

    main()

    assert load_page_data(output_path) == {
        "source_pdf": "paper.pdf",
        "pages": [
            {
                "source_page": 1,
                "text": "",
            }
        ],
    }


def test_search_command_prints_page_citation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    page_data_path = tmp_path / "paper.json"

    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [
                {
                    "source_page": 1,
                    "text": "Attention connects tokens.",
                },
                {
                    "source_page": 2,
                    "text": "Attention uses attention weights.",
                },
            ],
        },
        page_data_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research-copilot",
            "search",
            str(page_data_path),
            "attention",
            "--chunk-size",
            "100",
            "--overlap",
            "0",
        ],
    )

    main()

    output = capsys.readouterr().out

    assert "Page 2 | score=2" in output
    assert "Attention uses attention weights." in output


def test_card_command_creates_markdown_draft(
    tmp_path: Path,
    monkeypatch,
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

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research-copilot",
            "card",
            str(page_data_path),
            str(output_path),
        ],
    )

    main()

    markdown = output_path.read_text(encoding="utf-8")
    assert 'status: "draft-needs-human-review"' in markdown
