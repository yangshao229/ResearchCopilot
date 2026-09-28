"""Keep displayed PDF equations out of model-generated translations.

PDF text extraction cannot reliably reconstruct mathematical typography.  This
module identifies conservative, standalone equation lines and keeps a region
of the original PDF page so the reader can see their exact printed form.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

FORMULA_MARKER_PATTERN = re.compile(r"\[\[RC_FORMULA_\d{2}\]\]")
SYMBOL_MARKER_PATTERN = re.compile(r"\[\[RC_SYMBOL_\d{2}\]\]")
_MATH_SYMBOLS = re.compile(r"[α-ωΑ-Ω∑∏∫∞√≤≥≠≈∈∉⊂⊆⊕⊗→←↔±×÷∂∇−]+")
_EQUATION_START = re.compile(r"^([A-Za-z][A-Za-z0-9]{2,})\b")


class FormulaRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marker: str
    source_page: int = Field(ge=1)
    left: float = Field(ge=0)
    top: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


def protect_display_formulas(
    pdf_path: Path, source_page: int, source_text: str
) -> tuple[str, list[FormulaRegion]]:
    """Replace confidently located display equations with image placeholders.

    Unrecognized math is intentionally left alone rather than misidentified.
    The returned boxes use PDF points with a top-left origin for PDF.js.
    """
    if not pdf_path.is_file():
        return source_text, []
    try:
        page = PdfReader(pdf_path).pages[source_page - 1]
    except (OSError, PdfReadError, IndexError):
        return source_text, []

    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    positions: list[tuple[str, float, float, float]] = []

    def visit_text(text: str, _cm: object, tm: list[float], _font: object, size: float) -> None:
        if text.strip():
            positions.append((text.strip(), float(tm[4]), float(tm[5]), float(size)))

    page.extract_text(visitor_text=visit_text)
    protected_text = source_text
    regions: list[FormulaRegion] = []
    used_positions: set[int] = set()

    for line in source_text.splitlines():
        expression = line.strip()
        if len(regions) >= 12 or not _is_display_equation(expression):
            continue
        match = _EQUATION_START.match(expression)
        if match is None:
            continue
        anchor = match.group(1)
        candidates = [
            (index, x, y, size)
            for index, (text, x, y, size) in enumerate(positions)
            if index not in used_positions and text.startswith(anchor)
        ]
        if len(candidates) != 1:
            continue
        index, x, y, size = candidates[0]
        if not (0 <= x < page_width and 0 <= y < page_height):
            continue
        used_positions.add(index)
        left = max(0.0, x - 12)
        right = min(page_width, max(x + 80, page_width - 65))
        top = max(0.0, page_height - y - max(17, size * 1.7))
        bottom = min(page_height, page_height - y + max(14, size * 1.4))
        marker = f"[[RC_FORMULA_{len(regions) + 1:02d}]]"
        if line not in protected_text:
            continue
        protected_text = protected_text.replace(line, marker, 1)
        regions.append(
            FormulaRegion(
                marker=marker,
                source_page=source_page,
                left=round(left, 2),
                top=round(top, 2),
                width=round(right - left, 2),
                height=round(bottom - top, 2),
            )
        )
    return protected_text, regions


def _is_display_equation(line: str) -> bool:
    if not line or len(line) > 150 or "=" not in line:
        return False
    if FORMULA_MARKER_PATTERN.search(line):
        return False
    if not _EQUATION_START.match(line):
        return False
    # A prose sentence containing an inline equals sign must stay translatable.
    if len(line.split()) > 16 or line.startswith(("The ", "This ", "While ", "In ")):
        return False
    return True


def validate_formula_markers(translation: str, regions: list[FormulaRegion]) -> bool:
    expected = {region.marker for region in regions}
    found = FORMULA_MARKER_PATTERN.findall(translation)
    return len(found) == len(expected) and set(found) == expected


def protect_math_symbols(source_text: str) -> tuple[str, dict[str, str]]:
    """Mask Unicode math glyphs that survived PDF extraction exactly."""
    replacements: dict[str, str] = {}

    def substitute(match: re.Match[str]) -> str:
        if len(replacements) >= 32:
            return match.group()
        marker = f"[[RC_SYMBOL_{len(replacements) + 1:02d}]]"
        replacements[marker] = match.group()
        return marker

    return _MATH_SYMBOLS.sub(substitute, source_text), replacements


def restore_math_symbols(translation: str, replacements: dict[str, str]) -> str | None:
    found = SYMBOL_MARKER_PATTERN.findall(translation)
    if len(found) != len(replacements) or set(found) != set(replacements):
        return None
    for marker, symbol in replacements.items():
        translation = translation.replace(marker, symbol)
    return translation
