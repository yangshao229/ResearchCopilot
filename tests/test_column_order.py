from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from research_copilot.column_order import inspect_column_order
from research_copilot.domain import LanguagePolicy
from research_copilot.language_preferences import PaperLanguagePreferenceStore
from research_copilot.page_layout import extract_page_layout
from research_copilot.page_translation import PageTranslationService
from research_copilot.paper_glossary import PaperGlossaryStore
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


def _two_column_pdf(
    tmp_path: Path, *, interleaved: bool, full_width_caption: bool = False,
    narrow_gutter: bool = False,
) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    body_top = 710 if full_width_caption else 730
    left_text = (
        "Left paragraph sentence introduces background and motive."
        if narrow_gutter else "Left column research paragraph line {index:02d}."
    )
    left = [
        f"BT /F1 8 Tf 72 {body_top - 26 * index} Td "
        f"({left_text.format(index=index)}) Tj ET "
        for index in range(16)
    ]
    right = [
        f"BT /F1 8 Tf 310 {body_top - 26 * index} Td "
        f"(Right column research paragraph line {index:02d}.) Tj ET "
        for index in range(16)
    ]
    commands = (
        [item for pair in zip(left, right) for item in pair]
        if interleaved else left + right
    )
    if full_width_caption:
        caption = "FullWidthCaptionTextRepeatsAcrossThePageAndPassesTheMiddleOfThePageTwice"
        commands = [
            "BT /F1 8 Tf 310 782 Td (Table and caption right fragment one.) Tj ET ",
            f"BT /F1 8 Tf 72 770 Td ({caption}) Tj ET ",
            "BT /F1 8 Tf 310 758 Td (Table and caption right fragment two.) Tj ET ",
            f"BT /F1 8 Tf 72 746 Td ({caption}) Tj ET ",
        ] + commands
    stream = DecodedStreamObject()
    stream.set_data("".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / ("interleaved.pdf" if interleaved else "columnwise.pdf")
    with path.open("wb") as output:
        writer.write(output)
    return path


class _Source:
    def page_text(self, pdf_path: Path, _paper_id: str, source_page: int) -> str:
        return PdfReader(pdf_path).pages[source_page - 1].extract_text()


class _Model:
    provider_name = "fake"
    model_name = "fake-translation"

    def __init__(self) -> None:
        self.calls = 0

    def translate(self, source_text: str, _policy: LanguagePolicy, _terms: list) -> str:
        self.calls += 1
        return source_text


def test_two_column_page_in_column_order_is_review_not_blocked(tmp_path: Path) -> None:
    pdf_path = _two_column_pdf(tmp_path, interleaved=False)
    audit = inspect_column_order(pdf_path, 1)
    assert audit.status == "column_candidate"
    assert audit.right_to_left_returns == 0

    model = _Model()
    service = PageTranslationService(
        _Source(), PaperGlossaryStore(tmp_path / "glossary"),
        tmp_path / "translations", model,
    )
    quality = service.quality(pdf_path, "ordered", 1)
    assert quality.status == "review"
    assert "column_order_review" in quality.issues
    service.translate(pdf_path, "ordered", 1, LanguagePolicy())
    assert model.calls == 1


def test_interleaved_columns_block_before_translation_or_cache(tmp_path: Path) -> None:
    pdf_path = _two_column_pdf(tmp_path, interleaved=True)
    audit = inspect_column_order(pdf_path, 1)
    assert audit.status == "interleaved"
    assert audit.right_to_left_returns >= 2

    model = _Model()
    service = PageTranslationService(
        _Source(), PaperGlossaryStore(tmp_path / "glossary"),
        tmp_path / "translations", model,
    )
    quality = service.quality(pdf_path, "mixed", 1)
    assert quality.status == "blocked"
    assert "column_order_mismatch" in quality.issues
    with pytest.raises(ValueError, match="左右栏间交错"):
        service.translate(pdf_path, "mixed", 1, LanguagePolicy())
    with pytest.raises(ValueError, match="左右栏间交错"):
        service.cached(pdf_path, "mixed", 1, LanguagePolicy())
    assert model.calls == 0


def test_full_width_caption_does_not_make_body_look_interleaved(tmp_path: Path) -> None:
    pdf_path = _two_column_pdf(
        tmp_path, interleaved=False, full_width_caption=True
    )
    audit = inspect_column_order(pdf_path, 1)
    assert audit.status == "column_candidate"
    assert audit.right_to_left_returns == 0


def test_narrow_two_column_gutter_does_not_merge_source_boxes(tmp_path: Path) -> None:
    pdf_path = _two_column_pdf(tmp_path, interleaved=False, narrow_gutter=True)
    layout = extract_page_layout(pdf_path, 1)
    midpoint = layout.page_width / 2
    assert layout.status == "ready"
    assert any(region.left < midpoint - 50 for region in layout.regions)
    assert any(region.left > midpoint for region in layout.regions)
    assert all(
        region.left + region.width < midpoint or region.left > midpoint
        for region in layout.regions
    )


def test_sparse_single_column_page_is_not_misclassified(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=792)
    path = tmp_path / "blank.pdf"
    with path.open("wb") as output:
        writer.write(output)
    assert inspect_column_order(path, 1).status == "not_detected"


def test_interleaved_page_is_blocked_by_http_endpoints(tmp_path: Path) -> None:
    papers = tmp_path / "papers"
    papers.mkdir()
    _two_column_pdf(papers, interleaved=True)
    model = _Model()
    service = PageTranslationService(
        _Source(), PaperGlossaryStore(tmp_path / "glossary"),
        tmp_path / "translations", model,
    )
    app = create_app(
        paper_directory=papers,
        frontend_directory=tmp_path / "missing-frontend",
        history_store=ReadingHistoryStore(tmp_path / "history"),
        language_preference_store=PaperLanguagePreferenceStore(tmp_path / "language"),
        page_translation_service=service,
    )
    client = TestClient(app)
    paper_id = client.get("/api/papers").json()[0]["id"]
    base = f"/api/papers/{paper_id}/pages/1"
    assert client.get(f"{base}/quality").json()["status"] == "blocked"
    assert client.get(f"{base}/translation").status_code == 422
    assert client.post(f"{base}/translation", json={"refresh": False}).status_code == 422
    assert model.calls == 0
