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
    assert len(guide.questions) == 4


def test_reading_guide_does_not_repeat_main_task_for_appendix() -> None:
    guide = build_reading_guide(
        PaperStructure(
            page_count=25,
            method="bookmarks",
            sections=[
                section("1 Introduction", 1),
                section("4 Our Method", 4),
                section("5 Empirical Experiments", 5),
                section("8 Conclusion and Future Work", 12),
                section("A Large Language Models Still Need Parameter Updates", 16),
                section("D Hyperparameters Used in Experiments", 18),
            ],
        )
    )

    assert len(guide.questions) == 4
    assert all(question.source_page < 16 for question in guide.questions)


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
