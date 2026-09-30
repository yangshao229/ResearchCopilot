"""Conservatively audit the PDF text layer before translating a two-column page."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ColumnOrderStatus = Literal["unknown", "not_detected", "column_candidate", "interleaved"]


@dataclass(frozen=True)
class ColumnOrderAudit:
    status: ColumnOrderStatus
    left_lines: int = 0
    right_lines: int = 0
    right_to_left_returns: int = 0


def inspect_column_order(pdf_path: Path, source_page: int) -> ColumnOrderAudit:
    """Only flag clear repeated right-to-left jumps in PDF extraction order.

    Text positions are a detection signal, not a reconstructed reading order.
    Sparse, rotated or uncertain pages are deliberately left unclassified.
    """
    if source_page < 1 or not pdf_path.is_file():
        return ColumnOrderAudit("unknown")
    fragments: list[tuple[str, float]] = []
    try:
        page = PdfReader(pdf_path).pages[source_page - 1]
        if page.rotation % 360:
            return ColumnOrderAudit("unknown")
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        # Full-width titles, captions and tables can produce apparent R->L jumps
        # before the actual two-column body. Never judge those rows as body order.
        with pdfplumber.open(pdf_path) as visual_pdf:
            visual_page = visual_pdf.pages[source_page - 1]
            midpoint = float(visual_page.width) / 2
            crossing_words = [
                float(word["bottom"])
                for word in visual_page.extract_words()
                if float(word["x0"]) < midpoint - 4
                and float(word["x1"]) > midpoint + 4
            ]
            body_start = max(crossing_words, default=0.0) + 6

        def visit_text(text: str, _cm: object, tm: list[float], _font: object, _size: float) -> None:
            if len(text.strip()) < 24:
                return
            x, y = float(tm[4]), float(tm[5])
            if not (0 <= x <= width and 0 <= y <= height):
                return
            if height - y < body_start:
                return
            side = "L" if x <= width * 0.38 else "R" if x >= width * 0.49 else ""
            if side:
                fragments.append((side, height - y))

        page.extract_text(visitor_text=visit_text)
    except (OSError, PdfReadError, IndexError, ValueError, TypeError):
        return ColumnOrderAudit("unknown")

    left = [top for side, top in fragments if side == "L"]
    right = [top for side, top in fragments if side == "R"]
    if len(left) < 8 or len(right) < 8:
        return ColumnOrderAudit("not_detected", len(left), len(right))
    left_span, right_span = max(left) - min(left), max(right) - min(right)
    overlap = min(max(left), max(right)) - max(min(left), min(right))
    if min(left_span, right_span) < height * 0.35 or overlap < height * 0.25:
        return ColumnOrderAudit("not_detected", len(left), len(right))

    sequence = [side for side, _top in fragments]
    returns = sum(
        previous == "R" and current == "L"
        for previous, current in zip(sequence, sequence[1:])
    )
    status: ColumnOrderStatus = "interleaved" if returns >= 2 else "column_candidate"
    return ColumnOrderAudit(status, len(left), len(right), returns)
