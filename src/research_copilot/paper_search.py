from pathlib import Path
from typing import cast

from research_copilot.keyword_retriever import search_chunks
from research_copilot.page_store import load_page_data
from research_copilot.text_splitter import chunk_pages


def search_page_data(
    page_data_path: Path,
    query: str,
    chunk_size: int = 1000,
    overlap: int = 100,
    limit: int = 5,
) -> list[dict[str, int | str]]:
    page_data = load_page_data(page_data_path)

    pages = cast(
        list[dict[str, int | str]],
        page_data["pages"],
    )

    chunks = chunk_pages(
        pages,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    return search_chunks(
        query,
        chunks,
        limit=limit,
    )
