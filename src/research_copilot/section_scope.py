from __future__ import annotations

import re

from research_copilot.domain import ReadingScope
from research_copilot.paper_structure import PaperSection, PaperStructure

_NUMBERED_SECTION = re.compile(
    r"(?:\bsection|\bsubsection|\bchapter)\s*"
    r"(\d+(?:\.\d+){0,5})|"
    r"(?<!\d)(\d+(?:\.\d+){0,5})\s*"
    r"(?:节|章节|section|subsection|chapter)",
    re.IGNORECASE,
)
_SECTION_CUES = (
    "section",
    "subsection",
    "chapter",
    "章节",
    "章节内容",
    "部分",
    "节",
)
_TASK_WORDS = (
    "解释",
    "总结",
    "概括",
    "说明",
    "分析",
    "阅读",
    "梳理",
    "explain",
    "summarize",
    "summary",
    "describe",
    "analyze",
    "read",
)


def resolve_section_scope(
    query: str,
    structure: PaperStructure,
    *,
    forced_full_paper: bool = False,
) -> ReadingScope:
    """Resolve an explicitly named section; ambiguous intent stays full paper."""
    if forced_full_paper:
        return ReadingScope(note="已按全文范围检索。")

    if not structure.sections:
        if _contains_section_cue(query):
            return _fallback("论文目录不可用，已回退到全文检索。")
        return ReadingScope()

    numbered_match = _NUMBERED_SECTION.search(query)
    matches: list[PaperSection]
    if numbered_match:
        number = (numbered_match.group(1) or numbered_match.group(2)).casefold()
        matches = [
            section
            for section in structure.sections
            if _section_number(section.title) == number
        ]
        if not matches:
            return _fallback(
                f"未在目录中找到第 {number} 节，已回退到全文检索。"
            )
    elif _contains_section_cue(query) or _has_task_named_section(query, structure):
        target = _section_target(query)
        if not target:
            return _fallback("章节名称不够明确，已回退到全文检索。")
        normalized_target = _normalize(target)
        matches = [
            section
            for section in structure.sections
            if normalized_target in _section_names(section.title)
        ]
        if not matches:
            return _fallback(
                f"未在目录中找到“{target}”，已回退到全文检索。"
            )
    else:
        return ReadingScope()

    if len(matches) != 1:
        return _fallback("目录中有多个同名章节，已回退到全文检索。")

    section = matches[0]
    if section.source_page > structure.page_count:
        return _fallback(
            f"“{section.title}”的目录页码超出 PDF 页数，已回退到全文检索。"
        )
    ordered_sections = sorted(
        structure.sections,
        key=lambda item: item.source_page,
    )
    section_index = ordered_sections.index(section)
    end_page = structure.page_count
    for next_section in ordered_sections[section_index + 1 :]:
        if next_section.level <= section.level:
            if next_section.source_page <= section.source_page:
                return _fallback(
                    f"“{section.title}”与下一章节位于同一 PDF 页，无法只筛选该章节，已回退到全文检索。"
                )
            end_page = next_section.source_page - 1
            break

    return ReadingScope(
        kind="section",
        resolution="matched",
        section_title=section.title,
        start_page=section.source_page,
        end_page=end_page,
        note=(
            f"章节限定：{section.title}，PDF 第 {section.source_page}–{end_page} 页。"
            "页码按章节书签或标题推断；同一页内的相邻章节无法进一步分开。"
        ),
    )


def _contains_section_cue(query: str) -> bool:
    normalized = query.casefold()
    return any(cue in normalized for cue in _SECTION_CUES)


def _has_task_named_section(query: str, structure: PaperStructure) -> bool:
    normalized_query = _normalize(query)
    task_present = any(word in normalized_query for word in _TASK_WORDS)
    if not task_present:
        return False
    return any(
        name and name in normalized_query
        for section in structure.sections
        for name in _section_names(section.title)
        if not re.fullmatch(r"\d+(?:\.\d+)*", name)
    )


def _section_target(query: str) -> str:
    target = query.casefold()
    for word in _TASK_WORDS:
        target = target.replace(word, " ")
    for cue in sorted(_SECTION_CUES, key=len, reverse=True):
        target = target.replace(cue, " ")
    target = re.sub(r"\b(?:the|a|an|of|in|on|for|about)\b", " ", target)
    return " ".join(target.split()).strip(" ：:，,？?。.")


def _section_number(title: str) -> str:
    match = re.match(r"\s*(\d+(?:\.\d+)*)", title)
    return match.group(1).casefold() if match else ""


def _section_names(title: str) -> set[str]:
    normalized = _normalize(title)
    number = _section_number(title)
    names = {normalized}
    if number:
        names.add(_normalize(title[len(number) :]))
    return names


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.casefold()).strip()


def _fallback(note: str) -> ReadingScope:
    return ReadingScope(resolution="fallback", note=note)
