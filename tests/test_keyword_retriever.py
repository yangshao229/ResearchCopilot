from research_copilot.keyword_retriever import search_chunks


def test_search_chunks_ranks_matches_and_preserves_pages() -> None:
    chunks = [
        {
            "source_page": 1,
            "chunk_index": 0,
            "text": "Attention connects tokens.",
        },
        {
            "source_page": 2,
            "chunk_index": 0,
            "text": "Attention, attention, and more attention.",
        },
        {
            "source_page": 3,
            "chunk_index": 0,
            "text": "Convolutional networks process images.",
        },
    ]

    results = search_chunks("attention", chunks, limit=2)

    assert [
        (result["source_page"], result["score"])
        for result in results
    ] == [
        (2, 3),
        (1, 1),
    ]
