from __future__ import annotations

import re
from typing import Literal

from research_copilot.paper_answer_service import PaperAnswer
from research_copilot.paper_structure import PaperStructure

QuestionKind = Literal[
    "page_count",
    "section_list",
    "section_count",
    "paragraph_count",
    "content",
]


def classify_paper_question(question: str) -> QuestionKind:
    normalized = " ".join(question.casefold().split())

    if _matches(normalized, (r"多少\s*页", r"页数", r"how many pages?")):
        return "page_count"
    if _matches(
        normalized,
        (
            r"多少\s*(?:个)?(?:章节|章|节|大标题|小标题)",
            r"(?:章节|章|节|标题)\s*(?:总数|数量)",
            r"how many (?:sections|chapters|headings)?",
        ),
    ):
        return "section_count"
    if _matches(
        normalized,
        (
            r"(?:有|列出|显示|查看).*(?:哪些|什么).*(?:章节|标题)",
            r"(?:目录|论文结构|文章结构|章节列表|标题列表)",
            r"(?:大标题|小标题).*(?:是|有|包括|包含)",
            r"(?:outline|table of contents|section headings?)",
        ),
    ):
        return "section_list"
    if _matches(
        normalized,
        (r"多少\s*(?:个)?段落", r"一共.*段", r"how many paragraphs?"),
    ):
        return "paragraph_count"
    return "content"


def answer_structural_question(
    question: str,
    structure: PaperStructure,
) -> PaperAnswer | None:
    kind = classify_paper_question(question)
    if kind == "content":
        return None

    if kind == "page_count":
        return _local_answer(
            answer=f"这篇 PDF 一共有 {structure.page_count} 页。",
            explanation="页数直接读取自本地 PDF 文件，没有调用检索或大模型。",
            uncertainty="PDF 页码是文件页序，不一定等于论文正文印刷页码。",
        )

    if kind == "paragraph_count":
        return _local_answer(
            answer="目前不能可靠给出这篇 PDF 的段落总数。",
            explanation=(
                "PDF 保存的是页面上的文字位置，不保存统一的“段落”结构；"
                "双栏、公式、图注和断行都会让简单计数失真。你可以先查看目录，"
                "再按章节阅读或提问。"
            ),
            uncertainty="只有完成版面级段落解析并经人工核对后，段落统计才可信。",
            insufficient=True,
        )

    if not structure.sections:
        return _local_answer(
            answer="当前无法可靠识别这篇论文的章节结构。",
            explanation="；".join(structure.warnings),
            uncertainty="系统没有根据局部检索片段猜测全文目录。",
            insufficient=True,
        )

    if kind == "section_count":
        top_level_count = sum(section.level == 1 for section in structure.sections)
        return _local_answer(
            answer=(
                f"当前识别到 {top_level_count} 个一级章节、"
                f"{len(structure.sections)} 个各级标题。"
            ),
            explanation=_structure_explanation(structure),
            uncertainty=_structure_uncertainty(structure),
        )

    visible_sections = structure.sections[:30]
    outline = "\n".join(
        f"{'  ' * (section.level - 1)}- {section.title}（PDF 第 {section.source_page} 页）"
        for section in visible_sections
    )
    if len(structure.sections) > len(visible_sections):
        outline += f"\n- ……另有 {len(structure.sections) - len(visible_sections)} 个标题"
    return _local_answer(
        answer=outline,
        explanation=_structure_explanation(structure),
        uncertainty=_structure_uncertainty(structure),
    )


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _structure_explanation(structure: PaperStructure) -> str:
    if structure.method == "bookmarks":
        return "目录来自 PDF 自带书签；每个标题保留了可跳转的 PDF 页码。"
    return "目录由本地文本规则推断；每个标题保留了可跳转的 PDF 页码。"


def _structure_uncertainty(structure: PaperStructure) -> str:
    return "；".join(structure.warnings) or "PDF 书签可能与正文印刷目录存在差异。"


def _local_answer(
    answer: str,
    explanation: str,
    uncertainty: str,
    insufficient: bool = False,
) -> PaperAnswer:
    return PaperAnswer(
        answer=answer,
        explanation=explanation,
        citations=[],
        insufficient_evidence=insufficient,
        uncertainty=uncertainty,
        evidence=[],
        provider="local",
        model="paper-structure",
    )
