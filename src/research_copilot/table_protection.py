"""Keep simple ruled PDF tables visual instead of flattening their cells into prose."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

TABLE_MARKER_PATTERN = re.compile(r"\[\[RC_TABLE_\d{2}\]\]")


class TableRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marker: str
    source_page: int = Field(ge=1)
    left: float = Field(ge=0)
    top: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


def _ruled_bands(page: pdfplumber.page.Page) -> list[tuple[float, float, float, float]]:
    """Locate only groups of three or more long, parallel horizontal rules."""
    rules = sorted(
        (
            (float(line["x0"]), float(line["x1"]), float(line["top"]))
            for line in page.lines
            if abs(float(line["top"]) - float(line["bottom"])) < 1
            and float(line["x1"]) - float(line["x0"]) >= float(page.width) * 0.45
        ),
        key=lambda item: item[2],
    )
    groups: list[list[tuple[float, float, float]]] = []
    for rule in rules:
        group = next(
            (
                candidate for candidate in groups
                if abs(candidate[0][0] - rule[0]) <= 8
                and abs(candidate[0][1] - rule[1]) <= 8
                and 0 < rule[2] - candidate[-1][2] <= 80
            ),
            None,
        )
        if group is None:
            groups.append([rule])
        else:
            group.append(rule)
    return [
        (group[0][0], group[0][2], group[0][1], group[-1][2])
        for group in groups
        if len(group) >= 3 and 20 <= group[-1][2] - group[0][2] <= 250
    ]


def _unique_line(lines: list[str], fragment: str) -> int | None:
    matches = [index for index, line in enumerate(lines) if fragment in line]
    return matches[0] if len(matches) == 1 else None


def protect_ruled_tables(
    pdf_path: Path, source_page: int, source_text: str
) -> tuple[str, list[TableRegion]]:
    """Replace confidently bounded table rows with original-PDF clip markers.

    A caption above the rules and prose below remain ordinary translatable text.
    No table-cell interpretation is attempted. Ambiguity leaves the source alone.
    """
    if not pdf_path.is_file() or source_page < 1:
        return source_text, []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[source_page - 1]
            if page.rotation % 360:
                return source_text, []
            page_width, page_height = float(page.width), float(page.height)
            bands = _ruled_bands(page)
        if not bands:
            return source_text, []
        positions: list[tuple[str, float, float]] = []

        def visit_text(
            text: str, _cm: object, tm: list[float], _font: object, _size: float
        ) -> None:
            if text.strip():
                positions.append((text.strip(), float(tm[4]), page_height - float(tm[5])))

        PdfReader(pdf_path).pages[source_page - 1].extract_text(visitor_text=visit_text)
    except (OSError, PdfReadError, IndexError, ValueError):
        return source_text, []

    lines = source_text.splitlines(keepends=True)
    candidates: list[tuple[int, int, tuple[float, float, float, float]]] = []
    for left, top, right, bottom in bands:
        inside = sorted(
            (
                (text, x, y) for text, x, y in positions
                if left - 2 <= x <= right + 2 and top + 2 <= y <= bottom - 2
            ),
            key=lambda item: (item[2], item[1]),
        )
        anchors = [item for item in inside if len(item[0]) >= 12]
        if (
            len(anchors) < 2
            or len({round(y / 5) for _text, _x, y in inside}) < 3
            or not inside
            or max(x for _text, x, _y in inside) - min(x for _text, x, _y in inside)
            < page_width * 0.3
        ):
            continue
        first = _unique_line(lines, anchors[0][0])
        last = _unique_line(lines, anchors[-1][0])
        if first is None or last is None or not 2 <= last - first <= 20:
            continue
        candidates.append((first, last, (left, top, right, bottom)))

    # Reject overlapping matches rather than replacing an uncertain text range.
    candidates.sort()
    if len(candidates) > 12 or any(
        previous[1] >= current[0]
        for previous, current in zip(candidates, candidates[1:])
    ):
        return source_text, []
    regions: list[TableRegion] = []
    for first, last, (left, top, right, bottom) in reversed(candidates):
        marker = f"[[RC_TABLE_{len(candidates) - len(regions):02d}]]"
        last_line = lines[last]
        ending = last_line[len(last_line.rstrip("\r\n")):]
        lines[first:last + 1] = [marker + ending]
        regions.append(
            TableRegion(
                marker=marker,
                source_page=source_page,
                left=round(max(0.0, left - 6), 2),
                top=round(max(0.0, top - 5), 2),
                width=round(min(page_width, right + 6) - max(0.0, left - 6), 2),
                height=round(min(page_height, bottom + 5) - max(0.0, top - 5), 2),
            )
        )
    return "".join(lines), list(reversed(regions))


def validate_table_markers(translation: str, regions: list[TableRegion]) -> bool:
    expected = {region.marker for region in regions}
    found = TABLE_MARKER_PATTERN.findall(translation)
    return len(found) == len(expected) and set(found) == expected
