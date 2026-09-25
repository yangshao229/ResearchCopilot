from research_copilot.selection_context import build_selection_context


def test_selection_context_restores_the_matching_paragraph() -> None:
    page = (
        "Background information.\n\n"
        "The model uses a shared encoder. It improves the translation quality.\n\n"
        "A separate paragraph follows."
    )

    preview = build_selection_context(
        page,
        "improves the translation quality.",
        source_page=3,
    )

    assert preview.method == "paragraph"
    assert preview.source_page == 3
    assert preview.selected_text == "improves the translation quality."
    assert preview.context_text == (
        "The model uses a shared encoder. It improves the translation quality."
    )


def test_selection_context_does_not_treat_a_single_line_break_as_paragraph() -> None:
    page = "The model uses a shared\nencoder for reading papers."

    preview = build_selection_context(
        page,
        "shared encoder for",
        source_page=1,
    )

    assert preview.method == "selection_only"
    assert preview.context_text == "shared encoder for"
    assert "无法在该页" in preview.note or "整页" in preview.note


def test_selection_context_falls_back_when_selection_is_not_found() -> None:
    preview = build_selection_context(
        "A different page of this paper.",
        "selected text from another page",
        source_page=2,
    )

    assert preview.method == "selection_only"
    assert preview.context_text == preview.selected_text
    assert "无法在该页" in preview.note


def test_selection_context_falls_back_when_selection_is_ambiguous() -> None:
    preview = build_selection_context(
        "repeat phrase then repeat phrase",
        "repeat phrase",
        source_page=2,
    )

    assert preview.method == "selection_only"
    assert preview.context_text == "repeat phrase"


def test_selection_context_does_not_return_the_entire_page_as_context() -> None:
    page = "A short PDF page with a short selected phrase."

    preview = build_selection_context(page, "selected phrase", source_page=1)

    assert preview.method == "selection_only"
    assert preview.context_text == "selected phrase"
    assert "避免发送整页" in preview.note
