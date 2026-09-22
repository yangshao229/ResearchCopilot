from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from research_copilot.pdf_loader import load_pdf_pages

StructureMethod = Literal["bookmarks", "heuristic", "unavailable"]
SectionSource = Literal["bookmark", "heuristic"]
SectionConfidence = Literal["high", "medium"]


class PaperSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    level: int = Field(ge=1, le=6)
    source_page: int = Field(ge=1)
    source: SectionSource
    confidence: SectionConfidence


class PaperStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_count: int = Field(ge=0)
    sections: list[PaperSection]
    method: StructureMethod
    warnings: list[str] = Field(default_factory=list)


_NUMBERED_HEADING = re.compile(
    r"^\s*(?P<number>\d+(?:\.\d+)*\.?)\s+(?P<title>\S(?:.*\S)?)\s*$"
)
_CONVENTIONAL_HEADINGS = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "preliminaries",
    "method",
    "methods",
    "methodology",
    "approach",
    "model",
    "experiments",
    "experimental setup",
    "results",
    "evaluation",
    "analysis",
    "discussion",
    "limitations",
    "conclusion",
    "conclusions",
    "references",
    "acknowledgments",
    "acknowledgements",
    "appendix",
}


def extract_paper_structure(pdf_path: Path) -> PaperStructure:
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)
    bookmarked_sections = _sections_from_bookmarks(reader)
    if bookmarked_sections:
        return PaperStructure(
            page_count=page_count,
            sections=bookmarked_sections,
            method="bookmarks",
        )

    sections = infer_sections_from_pages(load_pdf_pages(pdf_path))
    if sections:
        return PaperStructure(
            page_count=page_count,
            sections=sections,
            method="heuristic",
            warnings=[
                "此 PDF 没有可用书签，目录由文本规则推断，请对照原文核对。"
            ],
        )

    return PaperStructure(
        page_count=page_count,
        sections=[],
        method="unavailable",
        warnings=[
            "未找到 PDF 书签，也无法从文本中可靠识别章节；系统不会伪造目录。"
        ],
    )


def infer_sections_from_pages(
    pages: list[dict[str, int | str]],
) -> list[PaperSection]:
    sections: list[PaperSection] = []
    seen: set[tuple[str, int]] = set()

    for page in pages:
        source_page = int(page["source_page"])
        text = str(page["text"])
        for raw_line in text.splitlines():
            line = " ".join(raw_line.strip().split())
            candidate = _heading_candidate(line, source_page)
            if candidate is None:
                continue

            key = (candidate.title.casefold(), candidate.source_page)
            if key in seen:
                continue
            seen.add(key)
            sections.append(candidate)

    return sections


def _heading_candidate(line: str, source_page: int) -> PaperSection | None:
    if not line or len(line) > 120 or len(line.split()) > 18:
        return None

    normalized = line.rstrip(":").strip()
    if normalized.casefold() in _CONVENTIONAL_HEADINGS:
        return PaperSection(
            title=normalized,
            level=1,
            source_page=source_page,
            source="heuristic",
            confidence="medium",
        )

    match = _NUMBERED_HEADING.fullmatch(line)
    if match is None:
        return None

    number = match.group("number").rstrip(".")
    title = match.group("title").strip()
    if not _looks_like_heading_title(title):
        return None

    return PaperSection(
        title=f"{match.group('number')} {title}",
        level=min(number.count(".") + 1, 6),
        source_page=source_page,
        source="heuristic",
        confidence="medium",
    )


def _looks_like_heading_title(title: str) -> bool:
    if len(title) < 2 or title.endswith((".", ",", ";")):
        return False
    if re.fullmatch(r"\d+(?:\.\d+)*", title):
        return False
    return any(character.isalpha() for character in title)


def _sections_from_bookmarks(reader: PdfReader) -> list[PaperSection]:
    try:
        outline = reader.outline
    except Exception:
        return []

    sections: list[PaperSection] = []

    def visit(items: list[Any], level: int) -> None:
        for item in items:
            if isinstance(item, list):
                visit(item, min(level + 1, 6))
                continue

            title = _bookmark_title(item)
            if not title:
                continue
            try:
                page_index = reader.get_destination_page_number(item)
            except Exception:
                continue
            if page_index is None or page_index < 0:
                continue
            sections.append(
                PaperSection(
                    title=title,
                    level=level,
                    source_page=page_index + 1,
                    source="bookmark",
                    confidence="high",
                )
            )

    if isinstance(outline, list):
        visit(outline, 1)
    return sections


def _bookmark_title(item: Any) -> str:
    title = getattr(item, "title", None)
    if not title and hasattr(item, "get"):
        title = item.get("/Title")
    return " ".join(str(title or "").strip().split())
