from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_copilot.domain import GlossaryEntry


ContextMethod = Literal["paragraph", "page_window", "selection_only"]
MAX_CONTEXT_CHARS = 2400
WINDOW_RADIUS_CHARS = 900


class SelectionContextPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_page: int = Field(ge=1)
    selected_text: str
    context_text: str
    method: ContextMethod
    note: str
    glossary_terms: list[GlossaryEntry] = Field(default_factory=list)


def build_selection_context(
    page_text: str,
    selected_text: str,
    source_page: int,
) -> SelectionContextPreview:
    selected = " ".join(selected_text.split())
    page = page_text or ""
    normalized_page, offsets = _normalize_with_offsets(page)
    normalized_selected = " ".join(selected.split())

    if not selected or not normalized_selected:
        return _selection_only(source_page, selected, "没有可用的选区文本。")

    first_match = normalized_page.find(normalized_selected)
    if first_match < 0 or normalized_page.find(
        normalized_selected, first_match + 1
    ) >= 0:
        return _selection_only(
            source_page,
            selected,
            "无法在该页 PDF 文本中唯一定位选区；为避免拼错上下文，只发送精确选区。",
        )

    match_end = first_match + len(normalized_selected)
    original_start = offsets[first_match][0]
    original_end = offsets[match_end - 1][1]

    paragraph_start = page.rfind("\n\n", 0, original_start)
    paragraph_start = 0 if paragraph_start < 0 else paragraph_start + 2
    paragraph_end = page.find("\n\n", original_end)
    paragraph_end = len(page) if paragraph_end < 0 else paragraph_end
    paragraph = " ".join(page[paragraph_start:paragraph_end].split())

    if paragraph and paragraph == normalized_page and len(paragraph) <= MAX_CONTEXT_CHARS:
        return _selection_only(
            source_page,
            selected,
            "该页没有可靠段落边界且会暴露整页内容；为避免发送整页，只发送精确选区。",
        )

    if paragraph and len(paragraph) <= MAX_CONTEXT_CHARS:
        return SelectionContextPreview(
            source_page=source_page,
            selected_text=selected,
            context_text=paragraph,
            method="paragraph",
            note="已从同一 PDF 页恢复选区所在段落；译文只针对精确选区。",
        )

    if paragraph == normalized_page and len(paragraph) > MAX_CONTEXT_CHARS:
        context = _centered_window(normalized_page, (first_match, match_end))
        return SelectionContextPreview(
            source_page=source_page,
            selected_text=selected,
            context_text=context,
            method="page_window",
            note="该页没有可靠段落边界；已截取包含选区的同页有限上下文，译文只针对精确选区。",
        )

    if paragraph and len(paragraph) > MAX_CONTEXT_CHARS:
        context = _centered_window(paragraph, _relative_position(
            page[paragraph_start:paragraph_end],
            original_start - paragraph_start,
            original_end - paragraph_start,
        ))
        return SelectionContextPreview(
            source_page=source_page,
            selected_text=selected,
            context_text=context,
            method="page_window",
            note="段落过长，已截取包含选区的同页有限上下文；译文只针对精确选区。",
        )

    normalized_context = " ".join(page.split())
    normalized_start = _normalized_index_for_original(offsets, original_start)
    normalized_end = _normalized_index_for_original(offsets, original_end)
    context = _centered_window(
        normalized_context,
        (normalized_start, normalized_end),
    )
    if context == normalized_context:
        return _selection_only(
            source_page,
            selected,
            "无法在不发送整页的情况下截取可靠上下文；只发送精确选区。",
        )
    if not context or normalized_selected not in context:
        return _selection_only(
            source_page,
            selected,
            "该页没有可靠段落边界可供恢复；为避免发送整页，只发送精确选区。",
        )
    return SelectionContextPreview(
        source_page=source_page,
        selected_text=selected,
        context_text=context,
        method="page_window",
        note="PDF 文本层未提供可靠段落边界；已截取同页有限上下文，译文只针对精确选区。",
    )


def _selection_only(
    source_page: int,
    selected_text: str,
    note: str,
) -> SelectionContextPreview:
    return SelectionContextPreview(
        source_page=source_page,
        selected_text=selected_text,
        context_text=selected_text,
        method="selection_only",
        note=note,
    )


def _normalize_with_offsets(text: str) -> tuple[str, list[tuple[int, int]]]:
    normalized: list[str] = []
    offsets: list[tuple[int, int]] = []
    for match in re.finditer(r"\s+|\S+", text):
        if match.group().isspace():
            normalized.append(" ")
            offsets.append((match.start(), match.end()))
        else:
            normalized.append(match.group())
            offsets.extend(
                (position, position + 1)
                for position in range(match.start(), match.end())
            )
    joined = "".join(normalized)
    leading = len(joined) - len(joined.lstrip())
    content = joined.strip()
    return content, offsets[leading : leading + len(content)]


def _relative_position(
    paragraph: str,
    original_start: int,
    original_end: int,
) -> tuple[int, int]:
    normalized, offsets = _normalize_with_offsets(paragraph)
    start = _normalized_index_for_original(offsets, original_start)
    end = _normalized_index_for_original(offsets, original_end)
    return start, max(start + 1, end)


def _normalized_index_for_original(
    offsets: list[tuple[int, int]],
    original_offset: int,
) -> int:
    for index, (start, end) in enumerate(offsets):
        if start <= original_offset < end:
            return index
    return len(offsets)


def _centered_window(text: str, selection: tuple[int, int]) -> str:
    start, end = selection
    if end - start >= MAX_CONTEXT_CHARS:
        start = max(start, end - MAX_CONTEXT_CHARS)
    left = max(0, start - WINDOW_RADIUS_CHARS)
    right = min(len(text), max(end, start + WINDOW_RADIUS_CHARS))
    if right - left > MAX_CONTEXT_CHARS:
        overflow = right - left - MAX_CONTEXT_CHARS
        left = min(max(0, left + overflow // 2), start)
        right = min(len(text), left + MAX_CONTEXT_CHARS)
    return text[left:right].strip()
