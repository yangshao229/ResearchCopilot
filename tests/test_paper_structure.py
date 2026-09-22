from pathlib import Path

from pypdf import PdfWriter

from research_copilot.paper_structure import (
    extract_paper_structure,
    infer_sections_from_pages,
)


def test_extract_paper_structure_uses_pdf_bookmarks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "bookmarked.pdf"
    writer = PdfWriter()
    for _ in range(4):
        writer.add_blank_page(width=72, height=72)
    introduction = writer.add_outline_item("1 Introduction", 0)
    writer.add_outline_item("1.1 Motivation", 1, parent=introduction)
    writer.add_outline_item("2 Method", 2)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    structure = extract_paper_structure(pdf_path)

    assert structure.method == "bookmarks"
    assert structure.page_count == 4
    assert [section.title for section in structure.sections] == [
        "1 Introduction",
        "1.1 Motivation",
        "2 Method",
    ]
    assert [section.level for section in structure.sections] == [1, 2, 1]
    assert [section.source_page for section in structure.sections] == [1, 2, 3]
    assert all(section.confidence == "high" for section in structure.sections)


def test_infer_sections_from_page_text_is_conservative() -> None:
    sections = infer_sections_from_pages(
        [
            {
                "source_page": 1,
                "text": "Abstract\nThis paper studies attention.\n1 Introduction",
            },
            {
                "source_page": 2,
                "text": (
                    "1.1 Motivation\n"
                    "This is a complete sentence and should not be a heading.\n"
                    "2 Method\n"
                    "[12] A reference entry"
                ),
            },
        ]
    )

    assert [section.title for section in sections] == [
        "Abstract",
        "1 Introduction",
        "1.1 Motivation",
        "2 Method",
    ]
    assert [section.level for section in sections] == [1, 1, 2, 1]
    assert all(section.source == "heuristic" for section in sections)


def test_extract_paper_structure_reports_unavailable_without_guessing(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    structure = extract_paper_structure(pdf_path)

    assert structure.method == "unavailable"
    assert structure.sections == []
    assert "不会伪造目录" in structure.warnings[0]
