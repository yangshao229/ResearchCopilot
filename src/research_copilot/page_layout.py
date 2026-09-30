"""Read-only source regions for checking extracted text against the PDF page."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field

MAX_SOURCE_REGIONS = 80


class PageSourceRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_page: int = Field(ge=1)
    text: str = Field(min_length=1)
    left: float = Field(ge=0)
    top: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class PageLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_page: int = Field(ge=1)
    page_width: float = Field(gt=0)
    page_height: float = Field(gt=0)
    status: Literal["ready", "no_text", "unsupported_rotation"]
    order_verified: bool = False
    risk_flags: list[
        Literal["multi_column_candidate", "table_rulings_candidate", "small_glyph_fragments"]
    ] = Field(default_factory=list)
    truncated: bool = False
    regions: list[PageSourceRegion]


@dataclass
class _Draft:
    text_lines: list[str]
    left: float
    top: float
    right: float
    bottom: float


def _join_words(words: list[dict[str, object]]) -> str:
    result = ""
    for word in words:
        token = str(word["text"])
        if not result:
            result = token
        elif "\u3400" <= result[-1] <= "\u9fff" and "\u3400" <= token[0] <= "\u9fff":
            result += token
        else:
            result += " " + token
    return result


def _visual_lines(page: pdfplumber.page.Page) -> list[dict[str, object]]:
    """Split words on the same row at wide gutters, instead of merging columns."""
    words = page.extract_words(x_tolerance=1, y_tolerance=2)
    rows: list[list[dict[str, object]]] = []
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        candidate = next(
            (
                row for row in rows
                if abs(float(word["top"]) - float(row[0]["top"])) <= 2.5
            ),
            None,
        )
        if candidate is None:
            rows.append([word])
        else:
            candidate.append(word)
    visual_lines: list[dict[str, object]] = []
    gutter = max(24.0, float(page.width) * 0.06)
    midpoint = float(page.width) / 2
    for row in rows:
        row.sort(key=lambda word: float(word["x0"]))
        segments: list[list[dict[str, object]]] = []
        for word in row:
            gap = (
                float(word["x0"]) - float(segments[-1][-1]["x1"])
                if segments else 0.0
            )
            crosses_center_gutter = bool(segments) and (
                float(segments[-1][-1]["x1"]) < midpoint - 3
                and float(word["x0"]) > midpoint + 3
                and gap >= 10
            )
            if not segments or gap > gutter or crosses_center_gutter:
                segments.append([word])
            else:
                segments[-1].append(word)
        for segment in segments:
            visual_lines.append(
                {
                    "text": _join_words(segment),
                    "x0": min(float(word["x0"]) for word in segment),
                    "top": min(float(word["top"]) for word in segment),
                    "x1": max(float(word["x1"]) for word in segment),
                    "bottom": max(float(word["bottom"]) for word in segment),
                }
            )
    return visual_lines


def _matches(draft: _Draft, line: dict[str, object]) -> bool:
    left = float(line["x0"])
    top = float(line["top"])
    right = float(line["x1"])
    bottom = float(line["bottom"])
    gap = max(0.0, top - draft.bottom)
    overlap = max(0.0, min(right, draft.right) - max(left, draft.left))
    narrower_width = min(right - left, draft.right - draft.left)
    return (
        gap <= 5.0
        and bottom >= draft.top
        and narrower_width > 0
        and overlap / narrower_width >= 0.55
        and abs(left - draft.left) <= 40
        and len(draft.text_lines) < 8
        and sum(map(len, draft.text_lines)) < 800
    )


def _region(page_number: int, draft: _Draft) -> PageSourceRegion:
    text = "\n".join(draft.text_lines)
    geometry = (draft.left, draft.top, draft.right, draft.bottom)
    fingerprint = f"{page_number}|{tuple(round(value, 2) for value in geometry)}|{text}"
    return PageSourceRegion(
        id=hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16],
        source_page=page_number,
        text=text,
        left=round(draft.left, 2),
        top=round(draft.top, 2),
        width=round(draft.right - draft.left, 2),
        height=round(draft.bottom - draft.top, 2),
    )


def _has_parallel_columns(drafts: list[_Draft], page_width: float) -> bool:
    """Detect only obvious, vertically overlapping left/right text islands."""
    midpoint = page_width / 2
    left = [
        draft for draft in drafts
        if draft.right < midpoint - 15 and sum(map(len, draft.text_lines)) >= 20
    ]
    right = [
        draft for draft in drafts
        if draft.left > midpoint + 15 and sum(map(len, draft.text_lines)) >= 20
    ]
    return any(
        min(a.bottom, b.bottom) - max(a.top, b.top) >= 6
        for a in left for b in right
    )


def _has_table_rulings(page: pdfplumber.page.Page) -> bool:
    """Flag table-like horizontal rules, not claim table recognition."""
    rules = [
        line for line in page.lines
        if abs(float(line["top"]) - float(line["bottom"])) < 1
        and float(line["x1"]) - float(line["x0"]) >= float(page.width) * 0.45
    ]
    for index, first in enumerate(rules):
        similar = [
            later for later in rules[index + 1:]
            if abs(float(later["x0"]) - float(first["x0"])) <= 8
            and abs(float(later["x1"]) - float(first["x1"])) <= 8
            and 8 <= float(later["top"]) - float(first["top"]) <= 180
        ]
        if len(similar) >= 2:
            return True
    return False


def extract_page_layout(pdf_path: Path, source_page: int) -> PageLayout:
    """Locate text in an unrotated page without claiming logical reading order."""
    if source_page < 1:
        raise ValueError("PDF 页码必须从 1 开始。")
    with pdfplumber.open(pdf_path) as pdf:
        if source_page > len(pdf.pages):
            raise ValueError("PDF 页码超出范围。")
        page = pdf.pages[source_page - 1]
        width, height = float(page.width), float(page.height)
        if page.rotation % 360:
            return PageLayout(
                source_page=source_page,
                page_width=width,
                page_height=height,
                status="unsupported_rotation",
                regions=[],
            )
        lines = _visual_lines(page)
        table_rulings = _has_table_rulings(page)

    valid_lines = [
        line
        for line in lines
        if isinstance(line.get("text"), str)
        and len(str(line["text"]).strip()) >= 3
        and 0 <= float(line["x0"]) < float(line["x1"]) <= width
        and 0 <= float(line["top"]) < float(line["bottom"]) <= height
    ]
    valid_lines.sort(key=lambda line: (float(line["top"]), float(line["x0"])))
    def is_small_annotation(line: dict[str, object]) -> bool:
        line_height = float(line["bottom"]) - float(line["top"])
        return line_height < 8 or (line_height < 9 and len(str(line["text"]).strip()) <= 12)

    main_lines = [line for line in valid_lines if not is_small_annotation(line)]
    small_lines = [line for line in valid_lines if is_small_annotation(line)]
    drafts: list[_Draft] = []
    for line in main_lines:
        candidate = next(
            (draft for draft in reversed(drafts) if _matches(draft, line)), None
        )
        if candidate is None:
            drafts.append(
                _Draft(
                    text_lines=[str(line["text"]).strip()],
                    left=float(line["x0"]),
                    top=float(line["top"]),
                    right=float(line["x1"]),
                    bottom=float(line["bottom"]),
                )
            )
        else:
            candidate.text_lines.append(str(line["text"]).strip())
            candidate.left = min(candidate.left, float(line["x0"]))
            candidate.top = min(candidate.top, float(line["top"]))
            candidate.right = max(candidate.right, float(line["x1"]))
            candidate.bottom = max(candidate.bottom, float(line["bottom"]))
    # Superscripts/subscripts are often extracted as tiny, mangled lines.
    # Include their pixels in a nearby source box without presenting them as prose.
    for line in small_lines:
        for draft in drafts:
            if (
                float(line["top"]) <= draft.bottom + 3
                and float(line["bottom"]) >= draft.top
                and float(line["x0"]) >= draft.left - 3
                and float(line["x1"]) <= draft.right + 3
            ):
                draft.top = min(draft.top, float(line["top"]))
                draft.bottom = max(draft.bottom, float(line["bottom"]))
                break
    risk_flags: list[
        Literal["multi_column_candidate", "table_rulings_candidate", "small_glyph_fragments"]
    ] = []
    if _has_parallel_columns(drafts, width):
        risk_flags.append("multi_column_candidate")
    if table_rulings:
        risk_flags.append("table_rulings_candidate")
    if len(small_lines) >= 5:
        risk_flags.append("small_glyph_fragments")
    return PageLayout(
        source_page=source_page,
        page_width=width,
        page_height=height,
        status="ready" if drafts else "no_text",
        risk_flags=risk_flags,
        truncated=len(drafts) > MAX_SOURCE_REGIONS,
        regions=[_region(source_page, draft) for draft in drafts[:MAX_SOURCE_REGIONS]],
    )
