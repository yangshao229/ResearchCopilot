from research_copilot.paper_structure import PaperSection, PaperStructure
from research_copilot.section_scope import resolve_section_scope


def sample_structure() -> PaperStructure:
    return PaperStructure(
        page_count=10,
        method="bookmarks",
        sections=[
            PaperSection(
                title="1 Introduction",
                level=1,
                source_page=1,
                source="bookmark",
                confidence="high",
            ),
            PaperSection(
                title="1.1 Motivation",
                level=2,
                source_page=2,
                source="bookmark",
                confidence="high",
            ),
            PaperSection(
                title="1.2 Limitations",
                level=2,
                source_page=4,
                source="bookmark",
                confidence="high",
            ),
            PaperSection(
                title="2 Method",
                level=1,
                source_page=5,
                source="bookmark",
                confidence="high",
            ),
            PaperSection(
                title="3 Results",
                level=1,
                source_page=8,
                source="bookmark",
                confidence="high",
            ),
        ],
    )


def test_numbered_subsection_uses_next_sibling_page_boundary() -> None:
    scope = resolve_section_scope("解释 1.1 节", sample_structure())

    assert scope.kind == "section"
    assert scope.resolution == "matched"
    assert scope.section_title == "1.1 Motivation"
    assert (scope.start_page, scope.end_page) == (2, 3)


def test_named_section_without_the_word_section_is_recognized() -> None:
    scope = resolve_section_scope("Summarize Results", sample_structure())

    assert scope.kind == "section"
    assert scope.section_title == "3 Results"
    assert (scope.start_page, scope.end_page) == (8, 10)


def test_unknown_or_ambiguous_section_falls_back_to_full_paper() -> None:
    unknown = resolve_section_scope("解释 9.9 节", sample_structure())
    duplicated_structure = sample_structure().model_copy(
        update={
            "sections": [
                *sample_structure().sections,
                PaperSection(
                    title="4 Results",
                    level=1,
                    source_page=9,
                    source="bookmark",
                    confidence="high",
                ),
            ]
        }
    )
    ambiguous = resolve_section_scope("Summarize Results", duplicated_structure)

    assert unknown.kind == "full_paper"
    assert unknown.resolution == "fallback"
    assert ambiguous.kind == "full_paper"
    assert ambiguous.resolution == "fallback"


def test_same_page_sibling_falls_back_instead_of_leaking_section_content() -> None:
    structure = sample_structure().model_copy(
        update={
            "sections": [
                sample_structure().sections[0],
                sample_structure().sections[1],
                sample_structure().sections[2].model_copy(
                    update={"source_page": 2}
                ),
                *sample_structure().sections[3:],
            ]
        }
    )

    scope = resolve_section_scope("解释 1.1 节", structure)

    assert scope.kind == "full_paper"
    assert scope.resolution == "fallback"


def test_user_can_explicitly_keep_full_paper_scope() -> None:
    scope = resolve_section_scope(
        "解释 1.1 节",
        sample_structure(),
        forced_full_paper=True,
    )

    assert scope.kind == "full_paper"
    assert scope.resolution == "full_paper"
