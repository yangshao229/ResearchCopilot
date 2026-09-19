import pytest

from research_copilot.text_splitter import chunk_pages


def test_chunk_pages_preserves_page_numbers_and_overlap() -> None:
    pages = [
        {"source_page": 1, "text": "abcdefghij"},
        {"source_page": 2, "text": "klmnop"},
    ]

    chunks = chunk_pages(pages, chunk_size=6, overlap=2)

    assert chunks == [
        {"source_page": 1, "chunk_index": 0, "text": "abcdef"},
        {"source_page": 1, "chunk_index": 1, "text": "efghij"},
        {"source_page": 2, "chunk_index": 0, "text": "klmnop"},
    ]


def test_chunk_pages_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_pages([], chunk_size=4, overlap=4)