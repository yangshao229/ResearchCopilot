from research_copilot.paper_reading_guide import build_reading_guide
from research_copilot.paper_structure import PaperSection, PaperStructure


def section(title: str, page: int) -> PaperSection:
    return PaperSection(
        title=title,
        level=1,
        source_page=page,
        source="bookmark",
        confidence="high",
    )


def test_reading_guide_uses_real_section_titles() -> None:
    guide = build_reading_guide(
        PaperStructure(
            page_count=12,
            method="bookmarks",
            sections=[
                section("Introduction", 2),
                section("Model Architecture", 4),
                section("Experiments", 7),
                section("Conclusion", 10),
            ],
        )
    )

    assert {question.role for question in guide.questions} == {
        "overview",
        "method",
        "experiments",
        "critique",
    }
    assert any("Model Architecture" in item.question for item in guide.questions)
    assert any(item.source_page == 7 for item in guide.questions)


def test_reading_guide_does_not_invent_experiment_questions() -> None:
    guide = build_reading_guide(
        PaperStructure(
            page_count=5,
            method="bookmarks",
            sections=[
                section("Introduction", 1),
                section("Formal Proof", 3),
                section("Conclusion", 5),
            ],
        )
    )

    assert all(question.role != "experiments" for question in guide.questions)


def test_reading_guide_refuses_generic_questions_without_structure() -> None:
    guide = build_reading_guide(
        PaperStructure(
            page_count=2,
            method="unavailable",
            sections=[],
        )
    )

    assert guide.questions == []
    assert "没有生成" in guide.warnings[0]
