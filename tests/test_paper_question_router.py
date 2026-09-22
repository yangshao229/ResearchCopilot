from research_copilot.paper_question_router import (
    answer_structural_question,
    classify_paper_question,
)
from research_copilot.paper_structure import PaperSection, PaperStructure


def bookmarked_structure() -> PaperStructure:
    return PaperStructure(
        page_count=15,
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
                title="2 Method",
                level=1,
                source_page=4,
                source="bookmark",
                confidence="high",
            ),
        ],
    )


def test_router_answers_page_count_locally() -> None:
    answer = answer_structural_question("这篇论文一共有多少页？", bookmarked_structure())

    assert answer is not None
    assert answer.answer == "这篇 PDF 一共有 15 页。"
    assert answer.provider == "local"
    assert answer.evidence == []


def test_router_lists_outline_with_page_numbers() -> None:
    answer = answer_structural_question("这篇论文有哪些大标题和小标题？", bookmarked_structure())

    assert answer is not None
    assert "1 Introduction（PDF 第 1 页）" in answer.answer
    assert "1.1 Motivation（PDF 第 2 页）" in answer.answer
    assert answer.insufficient_evidence is False


def test_router_does_not_fake_paragraph_count() -> None:
    answer = answer_structural_question("这一共有多少个段落？", bookmarked_structure())

    assert answer is not None
    assert "不能可靠" in answer.answer
    assert answer.insufficient_evidence is True
    assert answer.provider == "local"


def test_router_leaves_content_questions_for_rag() -> None:
    assert classify_paper_question("Transformer 为什么可以并行计算？") == "content"
    assert (
        answer_structural_question(
            "Transformer 为什么可以并行计算？",
            bookmarked_structure(),
        )
        is None
    )
