import pytest
from pydantic import ValidationError

from research_copilot.domain import ReadingContext


def test_reading_context_collects_stable_defaults() -> None:
    context = ReadingContext(
        paper_id="paper-id",
        query="What is the main contribution?",
    )

    assert context.session_id == "default"
    assert context.search_mode == "hybrid"
    assert context.scope.kind == "full_paper"
    assert context.language.explanation_language == "follow_question"


def test_reading_context_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ReadingContext(
            paper_id="paper-id",
            query="Question",
            unknown_option=True,
        )
