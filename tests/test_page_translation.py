from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from research_copilot.domain import LanguagePolicy
from research_copilot.formula_protection import (
    protect_display_formulas,
    protect_math_symbols,
    restore_math_symbols,
    validate_formula_markers,
)
from research_copilot.language_preferences import PaperLanguagePreferenceStore
from research_copilot.page_translation import (
    MAX_PAGE_TEXT_CHARS,
    DeepSeekPageTranslationModel,
    PageTranslationService,
)
from research_copilot.paper_answer_service import AnswerGenerationError
from research_copilot.paper_glossary import PaperGlossaryStore
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.table_protection import (
    TableRegion,
    protect_ruled_tables,
    validate_table_markers,
)
from research_copilot.web_app import create_app


class FakePageSource:
    def __init__(self) -> None:
        self.pages = {1: "Transformer uses attention.", 2: "Training uses Adam."}

    def page_text(self, _pdf_path: Path, _paper_id: str, source_page: int) -> str:
        return self.pages.get(source_page, "")


class FakeTranslationModel:
    provider_name = "fake"
    model_name = "fake-translation-v1"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def translate(self, source_text: str, policy: LanguagePolicy, terms: list) -> str:
        self.calls.append((source_text, policy.translation_target, len(terms)))
        return f"译文 {len(self.calls)}: {source_text}"


def make_service(tmp_path: Path) -> tuple[PageTranslationService, FakePageSource, FakeTranslationModel, PaperGlossaryStore]:
    source = FakePageSource()
    model = FakeTranslationModel()
    glossary = PaperGlossaryStore(tmp_path / "glossary")
    service = PageTranslationService(source, glossary, tmp_path / "translations", model)
    return service, source, model, glossary


def test_page_translation_is_explicit_cached_and_isolated(tmp_path: Path) -> None:
    service, source, model, glossary = make_service(tmp_path)
    policy = LanguagePolicy()
    pdf_path = tmp_path / "paper.pdf"

    assert service.cached(pdf_path, "paper-one", 1, policy) is None
    assert model.calls == []
    first = service.translate(pdf_path, "paper-one", 1, policy)
    assert first.source_page == 1
    assert first.target_language == "zh-CN"
    assert first.cache_hit is False
    assert service.translate(pdf_path, "paper-one", 1, policy).cache_hit is True
    assert len(model.calls) == 1

    service.translate(pdf_path, "paper-one", 2, policy)
    service.translate(pdf_path, "paper-two", 1, policy)
    english = policy.model_copy(update={"translation_target": "en"})
    service.translate(pdf_path, "paper-one", 1, english)
    assert len(model.calls) == 4

    glossary.add_entry("paper-one", "Transformer", "变换器", "zh-CN")
    service.translate(pdf_path, "paper-one", 1, policy)
    assert model.calls[-1] == (source.pages[1], "zh-CN", 1)
    assert len(model.calls) == 5

    source.pages[1] = "Transformer uses cross-attention."
    service.translate(pdf_path, "paper-one", 1, policy)
    assert len(model.calls) == 6
    service.translate(pdf_path, "paper-one", 1, policy, refresh=True)
    assert len(model.calls) == 7

    preserve_english = policy.model_copy(update={"terminology_policy": "preserve_english"})
    service.translate(pdf_path, "paper-one", 1, preserve_english)
    assert len(model.calls) == 8


def test_page_translation_rejects_missing_or_overlong_text(tmp_path: Path) -> None:
    service, source, model, _ = make_service(tmp_path)
    with pytest.raises(ValueError, match="没有可抽取的文字"):
        service.translate(tmp_path / "paper.pdf", "paper-one", 3, LanguagePolicy())
    source.pages[1] = "a" * (MAX_PAGE_TEXT_CHARS + 1)
    with pytest.raises(ValueError, match="过长"):
        service.translate(tmp_path / "paper.pdf", "paper-one", 1, LanguagePolicy())
    assert model.calls == []


def test_page_translation_api_reads_cache_without_model_call(tmp_path: Path) -> None:
    paper_directory = tmp_path / "papers"
    paper_directory.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_path = paper_directory / "paper.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)
    service, _, model, _ = make_service(tmp_path)
    app = create_app(
        paper_directory=paper_directory,
        frontend_directory=tmp_path / "missing-frontend",
        history_store=ReadingHistoryStore(tmp_path / "history"),
        language_preference_store=PaperLanguagePreferenceStore(tmp_path / "language"),
        page_translation_service=service,
    )
    client = TestClient(app)
    paper_id = client.get("/api/papers").json()[0]["id"]
    url = f"/api/papers/{paper_id}/pages/1/translation"

    assert client.get(url).json() is None
    assert model.calls == []
    response = client.post(url, json={"refresh": False})
    assert response.status_code == 200
    assert response.json()["translated_text"].startswith("译文")
    assert client.get(url).json()["cache_hit"] is True
    assert len(model.calls) == 1
    assert client.get(f"/api/papers/{paper_id}/pages/3/translation").status_code == 422
    assert client.post(f"/api/papers/missing/pages/1/translation", json={}).status_code == 404


def test_deepseek_page_translation_sends_only_selected_page_text() -> None:
    requests = []

    class Response:
        status_code = 200

        def json(self) -> dict:
            return {"output_text": '{"translated_text":"这是译文。"}'}

    def post(url: str, **kwargs):
        requests.append((url, kwargs))
        return Response()

    model = DeepSeekPageTranslationModel(api_key="test-key", post=post)
    output = model.translate("Only page one text.", LanguagePolicy(), [])

    assert output == "这是译文。"
    assert len(requests) == 1
    assert "Only page one text." in requests[0][1]["json"]["input"]
    assert "整篇" not in requests[0][1]["json"]["input"]
    assert requests[0][1]["json"]["reasoning"] == {"effort": "none"}


def test_incomplete_deepseek_translation_reports_token_limit_instead_of_bad_json() -> None:
    class Response:
        status_code = 200

        def json(self) -> dict:
            return {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            }

    model = DeepSeekPageTranslationModel(
        api_key="test-key", post=lambda _url, **_kwargs: Response()
    )
    with pytest.raises(AnswerGenerationError, match="token 上限"):
        model.translate("Only page one text.", LanguagePolicy(), [])


def test_deepseek_does_not_accept_untranslated_long_english_page() -> None:
    import json

    source = "The model updates low rank matrices during adaptation. " * 20

    class Response:
        status_code = 200

        def json(self) -> dict:
            return {"output_text": json.dumps({"translated_text": source})}

    model = DeepSeekPageTranslationModel(
        api_key="test-key", post=lambda _url, **_kwargs: Response()
    )
    with pytest.raises(AnswerGenerationError, match="仍主要是英文"):
        model.translate(source, LanguagePolicy(), [])


def test_formula_markers_must_be_preserved_exactly_once() -> None:
    from research_copilot.formula_protection import FormulaRegion

    regions = [
        FormulaRegion(
            marker="[[RC_FORMULA_01]]",
            source_page=5,
            left=200,
            top=500,
            width=250,
            height=30,
        )
    ]
    assert validate_formula_markers("解释\n[[RC_FORMULA_01]]", regions)
    assert not validate_formula_markers("解释省略了公式", regions)
    assert not validate_formula_markers("[[RC_FORMULA_01]] [[RC_FORMULA_01]]", regions)
    assert not validate_formula_markers("[[RC_FORMULA_02]]", regions)


def test_math_symbols_are_restored_exactly_and_missing_markers_fail() -> None:
    protected, replacements = protect_math_symbols("softmax is set to −∞; β≥0")
    assert "−∞" not in protected
    assert "β≥" not in protected
    assert restore_math_symbols(f"中文解释：{protected}", replacements) == (
        "中文解释：softmax is set to −∞; β≥0"
    )
    assert restore_math_symbols("模型漏掉了符号", replacements) is None
    assert restore_math_symbols(protected + " [[RC_SYMBOL_01]]", replacements) is None


def test_page_translation_keeps_inline_special_glyphs(tmp_path: Path) -> None:
    service, source, model, _ = make_service(tmp_path)
    source.pages[1] = "Mask forbidden logits with −∞ before softmax."
    result = service.translate(tmp_path / "missing.pdf", "paper-one", 1, LanguagePolicy())
    assert "−∞" not in model.calls[0][0]
    assert "[[RC_SYMBOL_01]]" in model.calls[0][0]
    assert "−∞" in result.translated_text


def test_display_formula_is_not_sent_to_model_and_remains_page_anchored(tmp_path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
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
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 100 600 Td (The network computes an output.) Tj ET "
        b"BT /F1 12 Tf 100 550 Td (The dimension is dmodel = 512.) Tj ET "
        b"BT /F1 12 Tf 200 500 Td (FFN(x) = xW1 + b1) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf_path = tmp_path / "paper.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)

    source_text = PdfReader(pdf_path).pages[0].extract_text()
    source = FakePageSource()
    source.pages[1] = source_text
    model = FakeTranslationModel()
    service = PageTranslationService(
        source, PaperGlossaryStore(tmp_path / "glossary"), tmp_path / "translations", model
    )
    result = service.translate(pdf_path, "paper-one", 1, LanguagePolicy())

    assert "FFN(x) = xW1 + b1" not in model.calls[0][0]
    assert "The dimension is dmodel = 512." in model.calls[0][0]
    assert "[[RC_FORMULA_01]]" in model.calls[0][0]
    assert result.formula_regions[0].source_page == 1
    assert result.formula_regions[0].top > 0
    assert service.translate(pdf_path, "paper-one", 1, LanguagePolicy()).cache_hit

    class DropsFormula(FakeTranslationModel):
        def translate(self, source_text: str, policy: LanguagePolicy, terms: list) -> str:
            return "模型遗漏了公式"

    unsafe_service = PageTranslationService(
        source, PaperGlossaryStore(tmp_path / "glossary"), tmp_path / "unsafe", DropsFormula()
    )
    with pytest.raises(AnswerGenerationError, match="公式占位符"):
        unsafe_service.translate(pdf_path, "paper-one", 1, LanguagePolicy())
    assert unsafe_service.cached(pdf_path, "paper-one", 1, LanguagePolicy()) is None


def test_visual_formula_continuation_does_not_leave_math_fragment_in_prose(
    tmp_path: Path,
) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
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
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 10 Tf 160 600 Td (lrate = d-0.5) Tj ET "
        b"BT /F1 7 Tf 200 597 Td (model * min(step_num, warmup_steps) (3)) Tj ET "
        b"BT /F1 10 Tf 100 575 Td (This paragraph explains the formula.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf_path = tmp_path / "paper.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)

    source = (
        "lrate = d-0.5\n"
        "model * min(step_num, warmup_steps) (3)\n"
        "This paragraph explains the formula.\n"
    )
    protected, regions = protect_display_formulas(pdf_path, 1, source)
    assert protected == "[[RC_FORMULA_01]]\nThis paragraph explains the formula.\n"
    assert len(regions) == 1
    assert validate_formula_markers(protected, regions)


def test_ambiguous_formula_position_is_left_unmodified(tmp_path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
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
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 10 Tf 160 600 Td (lrate = d-0.5) Tj ET "
        b"BT /F1 10 Tf 160 500 Td (lrate = d-0.5) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf_path = tmp_path / "paper.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)

    source = "lrate = d-0.5\n"
    protected, regions = protect_display_formulas(pdf_path, 1, source)
    assert protected == source
    assert regions == []


def _ruled_table_pdf(tmp_path: Path) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
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
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 11 Tf 108 710 Td (Table 1 describes the results.) Tj ET "
        b"118 680 m 493 680 l S 118 650 m 493 650 l S 118 600 m 493 600 l S "
        b"BT /F1 11 Tf 124 668 Td (Layer Type and Complexity per Layer) Tj ET "
        b"BT /F1 11 Tf 400 668 Td (Path Length) Tj ET "
        b"BT /F1 11 Tf 124 640 Td (Self-Attention) Tj ET "
        b"BT /F1 11 Tf 400 640 Td (O(1)) Tj ET "
        b"BT /F1 11 Tf 124 625 Td (Recurrent Layer) Tj ET "
        b"BT /F1 11 Tf 400 625 Td (O(n)) Tj ET "
        b"BT /F1 11 Tf 124 610 Td (Convolutional Layer) Tj ET "
        b"BT /F1 11 Tf 400 610 Td (O(log n)) Tj ET "
        b"BT /F1 11 Tf 108 570 Td (The next paragraph explains these results.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf_path = tmp_path / "ruled-table.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)
    return pdf_path


def test_ruled_table_is_protected_but_caption_and_prose_remain(tmp_path: Path) -> None:
    pdf_path = _ruled_table_pdf(tmp_path)
    source_text = PdfReader(pdf_path).pages[0].extract_text()
    protected, regions = protect_ruled_tables(pdf_path, 1, source_text)

    assert len(regions) == 1
    assert "Table 1 describes the results." in protected
    assert "The next paragraph explains these results." in protected
    assert "Self-Attention" not in protected
    assert "Convolutional Layer" not in protected
    assert protected.count("[[RC_TABLE_01]]") == 1
    assert regions[0].source_page == 1
    assert regions[0].width > 350

    source = FakePageSource()
    source.pages[1] = source_text
    model = FakeTranslationModel()
    service = PageTranslationService(
        source, PaperGlossaryStore(tmp_path / "glossary"), tmp_path / "translations", model
    )
    result = service.translate(pdf_path, "paper-one", 1, LanguagePolicy())
    assert "Self-Attention" not in model.calls[0][0]
    assert "The next paragraph explains these results." in model.calls[0][0]
    assert result.table_regions == regions


def test_ruled_table_uncertain_text_match_is_not_removed(tmp_path: Path) -> None:
    pdf_path = _ruled_table_pdf(tmp_path)
    source_text = PdfReader(pdf_path).pages[0].extract_text()
    ambiguous = source_text + "\nLayer Type and Complexity per Layer\n"
    protected, regions = protect_ruled_tables(pdf_path, 1, ambiguous)
    assert protected == ambiguous
    assert regions == []


def test_page_without_rules_is_not_marked_as_a_table(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    pdf_path = tmp_path / "plain.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)

    source_text = "A heading\nA paragraph with ordinary prose.\n"
    protected, regions = protect_ruled_tables(pdf_path, 1, source_text)
    assert protected == source_text
    assert regions == []


def test_table_marker_must_appear_exactly_once(tmp_path: Path) -> None:
    region = TableRegion(
        marker="[[RC_TABLE_01]]", source_page=1, left=100, top=100,
        width=300, height=90,
    )
    assert validate_table_markers("正文\n[[RC_TABLE_01]]", [region])
    assert not validate_table_markers("正文", [region])
    assert not validate_table_markers("[[RC_TABLE_01]] [[RC_TABLE_01]]", [region])

    pdf_path = _ruled_table_pdf(tmp_path)
    source = FakePageSource()
    source.pages[1] = PdfReader(pdf_path).pages[0].extract_text()

    class DropsTable(FakeTranslationModel):
        def translate(self, source_text: str, policy: LanguagePolicy, terms: list) -> str:
            return "只输出正文，遗漏原文表格"

    service = PageTranslationService(
        source, PaperGlossaryStore(tmp_path / "glossary"), tmp_path / "translations", DropsTable()
    )
    with pytest.raises(AnswerGenerationError, match="表格占位符"):
        service.translate(pdf_path, "paper-one", 1, LanguagePolicy())
    assert service.cached(pdf_path, "paper-one", 1, LanguagePolicy()) is None
