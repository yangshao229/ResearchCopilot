import hashlib
import json
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from pypdf import PdfReader

import research_copilot.formula_protection as formulas


PROJECT_ROOT = Path(__file__).parents[1]
TRUTH_PATH = (
    PROJECT_ROOT / "docs" / "evaluations" / "m7_4e_inline_math_truth.json"
)
EXPECTED_CASES = {
    "latex_beta_subscript": "protect",
    "latex_epsilon_exponent": "protect",
    "publisher_uppercase_gamma": "protect",
    "journal_eta_decimal": "protect",
    "greek_prose": "leave",
    "ordinary_english_equals": "leave",
    "ascii_variable_assignment": "safe_fallback",
    "function_expression": "safe_fallback",
    "duplicate_visual_occurrence": "safe_fallback",
    "duplicate_source_occurrence": "safe_fallback",
    "glyph_value_mismatch": "safe_fallback",
    "split_visual_rows": "safe_fallback",
    "rotated_page": "safe_fallback",
    "out_of_page_bounds": "safe_fallback",
}


class _Page:
    width = 612
    height = 792

    def __init__(self, chars: list[dict[str, object]], rotation: int) -> None:
        self.chars = chars
        self.rotation = rotation


class _Pdf:
    def __init__(self, page: _Page) -> None:
        self.pages = [page]

    def __enter__(self) -> "_Pdf":
        return self

    def __exit__(self, *_args: object) -> None:
        pass


def _load_cases() -> list[dict[str, object]]:
    payload = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    cases = payload["cases"]
    assert isinstance(cases, list)
    return cases


def _case_chars(case: dict[str, object]) -> list[dict[str, object]]:
    text = str(case["glyph_text"])
    copies = int(case.get("visual_copies", 1))
    split_after = int(case.get("split_after", len(text)))
    left = float(case.get("left", 20))
    chars: list[dict[str, object]] = []
    for copy_index in range(copies):
        x = left
        for index, letter in enumerate(text):
            if letter.isspace():
                x += 2
                continue
            top = 100.0 + copy_index * 50
            if index >= split_after:
                top += 20
            elif letter in "12" and chars and chars[-1]["text"] in "βη":
                top += 3
            chars.append({
                "text": letter,
                "x0": x,
                "x1": x + 5,
                "top": top,
                "bottom": top + 9,
            })
            x += 5
    return chars


def _run_case(
    monkeypatch: MonkeyPatch, tmp_path: Path, case: dict[str, object]
) -> tuple[str, list[formulas.FormulaRegion]]:
    pdf_path = tmp_path / f"{case['id']}.pdf"
    pdf_path.touch()
    page = _Page(_case_chars(case), int(case.get("rotation", 0)))
    monkeypatch.setattr(formulas.pdfplumber, "open", lambda _path: _Pdf(page))
    return formulas.protect_inline_assignments(
        pdf_path, 1, str(case["source_text"])
    )


def test_inline_math_truth_ledger_metrics(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    cases = _load_cases()
    assert len(cases) == len(EXPECTED_CASES)
    assert {case["id"]: case["expected"] for case in cases} == EXPECTED_CASES

    protected_hits = 0
    false_positives = 0
    safe_fallbacks = 0
    totals = {"protect": 0, "leave": 0, "safe_fallback": 0}

    for case in cases:
        expected = str(case["expected"])
        totals[expected] += 1
        protected, regions = _run_case(monkeypatch, tmp_path, case)
        if expected == "protect":
            protected_hits += int(len(regions) == 1)
            assert len(regions) == 1, case["id"]
            assert regions[0].inline, case["id"]
            assert regions[0].marker in protected, case["id"]
        else:
            if expected == "leave":
                false_positives += int(bool(regions))
            else:
                safe_fallbacks += int(not regions)
            assert not regions, case["id"]
            assert protected == case["source_text"], case["id"]

    supported_recall = protected_hits / totals["protect"]
    false_positive_rate = false_positives / totals["leave"]
    safe_fallback_rate = safe_fallbacks / totals["safe_fallback"]
    assert supported_recall == 1.0
    assert false_positive_rate == 0.0
    assert safe_fallback_rate == 1.0


def test_real_sample_page_keeps_three_inline_regions_without_modifying_pdf() -> None:
    pdf_path = PROJECT_ROOT / "data" / "raw" / "sample.pdf"
    if not pdf_path.is_file():
        pytest.skip("The optional local sample PDF is not synchronized with Git.")
    before = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    source = PdfReader(pdf_path).pages[6].extract_text() or ""

    protected, regions = formulas.protect_inline_assignments(pdf_path, 7, source)

    assert [region.marker for region in regions] == [
        "[[RC_FORMULA_01]]",
        "[[RC_FORMULA_02]]",
        "[[RC_FORMULA_03]]",
    ]
    assert all(region.inline and region.source_page == 7 for region in regions)
    assert all(
        0 <= region.left < 612
        and 0 < region.width <= 612 - region.left
        and 0 <= region.top < 792
        and 0 < region.height <= 792 - region.top
        for region in regions
    )
    assert "We used the Adam optimizer" in protected
    assert "We varied the learning" in protected
    assert "β1 = 0.9" not in protected
    assert "β2 = 0.98" not in protected
    assert "ϵ = 10−9" not in protected
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == before
