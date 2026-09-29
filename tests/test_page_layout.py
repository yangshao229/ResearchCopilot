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
    first[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
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
    with path.open("wb") as output:
        writer.write(output)


def test_page_layout_regions_have_stable_page_local_geometry(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    create_layout_pdf(pdf_path)

    layout = extract_page_layout(pdf_path, 1)
    assert layout.status == "ready"
    assert layout.order_verified is False
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
    assert client.get(f"{base}/4/layout").status_code == 422
    assert client.get(f"{base}/0/layout").status_code == 422
    assert client.get("/api/papers/missing/pages/1/layout").status_code == 404
