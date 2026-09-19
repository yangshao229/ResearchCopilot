from pathlib import Path
from typing import cast

from research_copilot.keyword_retriever import search_chunks
from research_copilot.page_store import load_page_data
from research_copilot.semantic_retriever import (
    DEFAULT_EMBEDDING_MODEL,
    E5EmbeddingModel,
    EmbeddingModel,
    semantic_search_chunks,
)
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


def semantic_search_page_data(
    page_data_path: Path,
    query: str,
    chunk_size: int = 1000,
    overlap: int = 100,
    limit: int = 5,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    embedding_model: EmbeddingModel | None = None,
) -> list[dict[str, int | float | str]]:
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
    model = embedding_model or E5EmbeddingModel(model_name)
    return semantic_search_chunks(
        query,
        chunks,
        model,
        limit=limit,
    )
