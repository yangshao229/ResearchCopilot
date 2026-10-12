import pytest

from research_copilot.context_window_evaluation import (
    contains_support,
    contains_support_on_one_page,
    expand_candidate_neighbours,
    window_text,
)


def test_window_stays_on_page_and_removes_verified_overlap() -> None:
    chunks = [
        {"source_page": 1, "chunk_index": 0, "text": "previous"},
        {"source_page": 2, "chunk_index": 0, "text": "alphaXYZ"},
        {"source_page": 2, "chunk_index": 1, "text": "XYZbeta"},
        {"source_page": 3, "chunk_index": 0, "text": "next page"},
    ]
    hit = {**chunks[1], "score": 1.0}

    assert window_text(hit, chunks, before=1, after=1, overlap=3) == "alphaXYZbeta"
    assert window_text(chunks[2], chunks, after=1, overlap=3) == "XYZbeta"


def test_window_rejects_stale_or_changed_chunk_text() -> None:
    chunks = [{"source_page": 2, "chunk_index": 0, "text": "current"}]

    with pytest.raises(ValueError, match="current PDF"):
        window_text({"source_page": 2, "chunk_index": 0, "text": "stale"}, chunks)


def test_two_neighbours_recover_fact_without_crossing_page() -> None:
    chunks = [
        {"source_page": 2, "chunk_index": 0, "text": "fact on old page"},
        {"source_page": 3, "chunk_index": 0, "text": "question context"},
        {"source_page": 3, "chunk_index": 1, "text": "intermediate text"},
        {"source_page": 3, "chunk_index": 2, "text": "answer fact"},
        {"source_page": 4, "chunk_index": 0, "text": "fact on next page"},
    ]

    assert window_text(chunks[1], chunks, after=1) == (
        "question context\nintermediate text"
    )
    assert window_text(chunks[1], chunks, after=2) == (
        "question context\nintermediate text\nanswer fact"
    )
    assert "fact on next page" not in window_text(chunks[1], chunks, after=3)


def test_support_markers_are_diagnostic_not_a_negative_gate() -> None:
    assert contains_support(["A fixed encoder and a BART generator."], ["BART generator"])
    assert not contains_support(["A fixed encoder."], ["BART generator"])
    assert contains_support(["Some unrelated result"], []) is None
    with pytest.raises(ValueError, match="must not be empty"):
        contains_support(["Some unrelated result"], ["  "])


def test_support_must_be_coherent_within_one_pdf_page() -> None:
    hits = [{"source_page": 2}, {"source_page": 4}]
    texts = ["first required fact", "second required fact"]
    markers = ["first required fact", "second required fact"]

    assert contains_support(texts, markers)
    assert not contains_support_on_one_page(hits, texts, markers)
    assert contains_support_on_one_page(
        [{"source_page": 4}, {"source_page": 4}], texts, markers
    )
    assert contains_support_on_one_page(hits, texts, []) is None
    with pytest.raises(ValueError, match="same length"):
        contains_support_on_one_page(hits, texts[:1], markers)


def test_candidate_neighbours_stay_on_page_and_keep_visible_hits_independent() -> None:
    chunks = [
        {"source_page": 1, "chunk_index": 0, "text": "previous page"},
        {"source_page": 2, "chunk_index": 0, "text": "alpha"},
        {"source_page": 2, "chunk_index": 1, "text": "beta"},
        {"source_page": 2, "chunk_index": 2, "text": "gamma"},
        {"source_page": 3, "chunk_index": 0, "text": "next page"},
    ]
    hits = [{**chunks[2], "score": 0.9}, {**chunks[1], "score": 0.8}]

    expanded = expand_candidate_neighbours(hits, chunks, before=1, after=1)

    assert [(item["source_page"], item["chunk_index"]) for item in expanded] == [
        (2, 1),
        (2, 0),
        (2, 2),
    ]
    assert expanded[:2] == hits
    assert all(item["source_page"] == 2 for item in expanded)


def test_candidate_neighbours_reject_stale_hits_and_invalid_sizes() -> None:
    chunks = [{"source_page": 2, "chunk_index": 0, "text": "current"}]

    with pytest.raises(ValueError, match="non-negative"):
        expand_candidate_neighbours(chunks, chunks, before=-1)
    with pytest.raises(ValueError, match="current PDF"):
        expand_candidate_neighbours(
            [{"source_page": 2, "chunk_index": 0, "text": "stale"}], chunks,
            after=1,
        )
