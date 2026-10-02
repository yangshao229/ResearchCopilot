from pathlib import Path

from pytest import MonkeyPatch

import research_copilot.formula_protection as formulas
from research_copilot.page_quality import inspect_page_text


def _chars(text: str, *, top: float = 100, left: float = 20) -> list[dict[str, object]]:
    chars: list[dict[str, object]] = []
    x = left
    for letter in text:
        if letter.isspace():
            x += 2
            continue
        raised = letter in "12" and chars and chars[-1]["text"] == "β"
        glyph_top = top + 3 if raised else top
        chars.append({
            "text": letter,
            "x0": x,
            "x1": x + 5,
            "top": glyph_top,
            "bottom": glyph_top + 9,
        })
        x += 5
    return chars


class _Page:
    width = 612
    height = 792
    rotation = 0

    def __init__(self, chars: list[dict[str, object]]) -> None:
        self.chars = chars


class _Pdf:
    def __init__(self, page: _Page) -> None:
        self.pages = [page]

    def __enter__(self) -> "_Pdf":
        return self

    def __exit__(self, *_args: object) -> None:
        pass


def _open_fake_pdf(
    monkeypatch: MonkeyPatch, tmp_path: Path, chars: list[dict[str, object]]
) -> Path:
    path = tmp_path / "paper.pdf"
    path.touch()
    monkeypatch.setattr(formulas.pdfplumber, "open", lambda _path: _Pdf(_Page(chars)))
    return path


def test_unique_inline_assignments_keep_prose_and_exact_clips(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    path = _open_fake_pdf(monkeypatch, tmp_path, _chars("β1=0.9 and β2=0.98"))
    source = "We used β1 = 0.9 and β2 = 0.98. More prose follows."
    protected, regions = formulas.protect_inline_assignments(
        path, 1, source, marker_start=3
    )

    assert protected == (
        "We used [[RC_FORMULA_03]] and [[RC_FORMULA_04]]. More prose follows."
    )
    assert [region.marker for region in regions] == [
        "[[RC_FORMULA_03]]", "[[RC_FORMULA_04]]"
    ]
    assert all(region.inline and region.width > 0 for region in regions)
    assert regions[0].left < regions[1].left
    assert formulas.validate_formula_markers(protected, regions)
    assert not formulas.validate_formula_markers(protected.replace(regions[0].marker, ""), regions)


def test_ambiguous_visual_or_source_match_is_not_replaced(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    chars = _chars("β1=0.9", top=100) + _chars("β1=0.9", top=200)
    path = _open_fake_pdf(monkeypatch, tmp_path, chars)
    source = "The parameter β1 = 0.9 is reported."
    assert formulas.protect_inline_assignments(path, 1, source) == (source, [])

    path = _open_fake_pdf(monkeypatch, tmp_path, _chars("β1=0.9"))
    repeated = "β1 = 0.9 occurs; β1 = 0.9 occurs again."
    assert formulas.protect_inline_assignments(path, 1, repeated) == (repeated, [])


def test_unmatched_or_missing_pdf_does_not_generate_fake_formula(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    source = "Use β1 = 0.9 in the model."
    assert formulas.protect_inline_assignments(tmp_path / "missing.pdf", 1, source) == (
        source, []
    )
    path = _open_fake_pdf(monkeypatch, tmp_path, _chars("β1=0.8"))
    assert formulas.protect_inline_assignments(path, 1, source) == (source, [])


def test_greek_math_requires_visual_review_even_without_protection() -> None:
    report = inspect_page_text(7, "Training used β1 = 0.9. " * 10, 1000)
    assert report.status == "review"
    assert "math_review" in report.issues

    prose = inspect_page_text(7, "Η θεωρία αυτή περιγράφει ένα σύστημα. " * 4, 1000)
    assert "math_review" not in prose.issues
