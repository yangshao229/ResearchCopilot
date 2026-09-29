from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from research_copilot.page_layout import extract_page_layout
from research_copilot.web_app import create_app


def create_layout_pdf(path: Path) -> None:
    writer = PdfWriter()
    first = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    first[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 50 700 Td (Left column first sentence.) Tj ET "
        b"BT /F1 12 Tf 50 685 Td (Left column second sentence.) Tj ET "
        b"BT /F1 12 Tf 350 700 Td (Right column first sentence.) Tj ET "
        b"BT /F1 12 Tf 350 685 Td (Right column second sentence.) Tj ET"
    )
    first[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792).rotate(90)
    table = writer.add_blank_page(width=612, height=792)
    table[NameObject("/Resources")] = first[NameObject("/Resources")]
    table_stream = DecodedStreamObject()
    table_stream.set_data(
        b"120 670 m 492 670 l S 120 650 m 492 650 l S "
        b"120 610 m 492 610 l S "
        b"BT /F1 12 Tf 130 675 Td (Results table) Tj ET"
    )
    table[NameObject("/Contents")] = writer._add_object(table_stream)
    math = writer.add_blank_page(width=612, height=792)
    math[NameObject("/Resources")] = first[NameObject("/Resources")]
    math_stream = DecodedStreamObject()
    math_stream.set_data(
        b"BT /F1 12 Tf 120 700 Td (A normal sentence describes this page.) Tj ET "
        + b" ".join(
            f"BT /F1 6 Tf 280 {670 - index * 12} Td (sub{index}) Tj ET".encode()
            for index in range(6)
        )
    )
    math[NameObject("/Contents")] = writer._add_object(math_stream)
    plain = writer.add_blank_page(width=612, height=792)
    plain[NameObject("/Resources")] = first[NameObject("/Resources")]
    plain_stream = DecodedStreamObject()
    plain_stream.set_data(
        b"BT /F1 12 Tf 50 700 Td "
        b"(This page has one ordinary paragraph with no table.) Tj ET "
        b"BT /F1 12 Tf 50 685 Td "
        b"(The second sentence continues in the same column.) Tj ET"
    )
    plain[NameObject("/Contents")] = writer._add_object(plain_stream)
    with path.open("wb") as output:
        writer.write(output)


def test_page_layout_regions_have_stable_page_local_geometry(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    create_layout_pdf(pdf_path)

    layout = extract_page_layout(pdf_path, 1)
    assert layout.status == "ready"
    assert layout.order_verified is False
    assert "multi_column_candidate" in layout.risk_flags
    assert layout.page_width == 612
    assert layout.page_height == 792
    assert len(layout.regions) == 2
    assert [region.text.splitlines()[0] for region in layout.regions] == [
        "Left column first sentence.",
        "Right column first sentence.",
    ]
    assert layout.regions[0].left == 50
    assert layout.regions[1].left == 350
    assert all(
        0 <= region.top < region.top + region.height <= 792
        for region in layout.regions
    )
    assert [region.id for region in layout.regions] == [
        region.id for region in extract_page_layout(pdf_path, 1).regions
    ]


def test_page_layout_fails_closed_on_unsupported_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    create_layout_pdf(pdf_path)
    assert extract_page_layout(pdf_path, 2).status == "no_text"
    rotated = extract_page_layout(pdf_path, 3)
    assert rotated.status == "unsupported_rotation"
    assert rotated.regions == []


def test_layout_flags_complex_page_candidates_without_claiming_order(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    create_layout_pdf(pdf_path)
    table = extract_page_layout(pdf_path, 4)
    math = extract_page_layout(pdf_path, 5)
    plain = extract_page_layout(pdf_path, 6)
    assert table.risk_flags == ["table_rulings_candidate"]
    assert math.risk_flags == ["small_glyph_fragments"]
    assert plain.risk_flags == []
    assert not table.order_verified and not math.order_verified


def test_layout_api_is_paper_scoped_and_validates_page(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    create_layout_pdf(paper_directory / "paper.pdf")
    client = TestClient(
        create_app(
            paper_directory=paper_directory,
            frontend_directory=tmp_path / "missing-frontend",
        )
    )
    paper_id = client.get("/api/papers").json()[0]["id"]
    base = f"/api/papers/{paper_id}/pages"
    assert client.get(f"{base}/1/layout").json()["regions"][0]["source_page"] == 1
    assert client.get(f"{base}/2/layout").json()["status"] == "no_text"
    assert client.get(f"{base}/7/layout").status_code == 422
    assert client.get(f"{base}/0/layout").status_code == 422
    assert client.get("/api/papers/missing/pages/1/layout").status_code == 404
