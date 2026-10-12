from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_copilot.paper_structure import PaperSection, PaperStructure

ReadingRole = Literal["overview", "method", "experiments", "critique"]


class ReadingQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ReadingRole
    label: str
    section_title: str
    question: str
    source_page: int = Field(ge=1)


class PaperReadingGuide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[ReadingQuestion]
    method: str
    warnings: list[str] = Field(default_factory=list)


_ROLE_KEYWORDS: dict[ReadingRole, tuple[str, ...]] = {
    "overview": ("abstract", "introduction", "background"),
    "method": (
        "method",
        "methodology",
        "approach",
        "model",
        "architecture",
        "algorithm",
        "framework",
    ),
    "experiments": (
        "experiment",
        "evaluation",
        "result",
        "benchmark",
        "ablation",
    ),
    "critique": ("limitation", "discussion", "conclusion", "future work"),
}


def build_reading_guide(structure: PaperStructure) -> PaperReadingGuide:
    if not structure.sections:
        return PaperReadingGuide(
            questions=[],
            method="unavailable",
            warnings=["没有可靠目录，因此没有生成与论文无关的通用问题。"],
        )

    questions: list[ReadingQuestion] = []
    selected_titles: set[str] = set()
    for role in ("overview", "method", "experiments", "critique"):
        matches = _sections_for_role(structure.sections, role)
        # The first matching main section is the reading route; later matches
        # often come from appendices and need not duplicate the same task.
        for section in matches[:1]:
            normalized_title = section.title.casefold()
            if normalized_title in selected_titles:
                continue
            selected_titles.add(normalized_title)
            questions.append(_question_for_section(role, section))

    if not questions:
        first_section = structure.sections[0]
        questions.append(
            ReadingQuestion(
                role="overview",
                label=f"先读 {first_section.title}",
                section_title=first_section.title,
                question=(
                    f"请解释 {first_section.title} 章节的核心内容，"
                    "并引用支持结论的原文页码。"
                ),
                source_page=first_section.source_page,
            )
        )

    return PaperReadingGuide(
        questions=questions,
        method=f"structure:{structure.method}",
        warnings=list(structure.warnings),
    )


def _sections_for_role(
    sections: list[PaperSection],
    role: ReadingRole,
) -> list[PaperSection]:
    keywords = _ROLE_KEYWORDS[role]
    return [
        section
        for section in sections
        if any(keyword in section.title.casefold() for keyword in keywords)
    ]


def _question_for_section(
    role: ReadingRole,
    section: PaperSection,
) -> ReadingQuestion:
    prompts: dict[ReadingRole, tuple[str, str]] = {
        "overview": (
            "理解问题",
            "作者在这一部分定义了什么研究问题，为什么它重要？",
        ),
        "method": (
            "拆解方法",
            "这一部分提出了什么方法？请说明输入、关键步骤和输出。",
        ),
        "experiments": (
            "检查证据",
            "这一部分用了什么实验设置和指标，结果支持了哪些结论？",
        ),
        "critique": (
            "批判阅读",
            "作者承认了哪些限制或未来方向？还有哪些结论需要谨慎看待？",
        ),
    }
    label_prefix, prompt = prompts[role]
    return ReadingQuestion(
        role=role,
        label=f"{label_prefix} · {section.title}",
        section_title=section.title,
        question=(
            f"阅读 {section.title}（PDF 第 {section.source_page} 页起）："
            f"{prompt}请引用具体原文页码。"
        ),
        source_page=section.source_page,
    )
