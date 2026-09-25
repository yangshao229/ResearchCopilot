from pathlib import Path
from typing import cast

from research_copilot.keyword_retriever import search_chunks
from research_copilot.hybrid_retriever import hybrid_search_chunks
from research_copilot.page_store import load_page_data
from research_copilot.semantic_retriever import (
    DEFAULT_EMBEDDING_MODEL,
    E5EmbeddingModel,
    EmbeddingModel,
    semantic_search_chunks,
)
from research_copilot.text_splitter import chunk_pages
from research_copilot.domain import ReadingScope


def search_page_data(
    page_data_path: Path,
    query: str,
    chunk_size: int = 1000,
    overlap: int = 100,
    limit: int = 5,
    scope: ReadingScope | None = None,
) -> list[dict[str, int | str]]:
    chunks = _load_chunks(page_data_path, chunk_size, overlap, scope)

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
    scope: ReadingScope | None = None,
) -> list[dict[str, int | float | str]]:
    chunks = _load_chunks(page_data_path, chunk_size, overlap, scope)
    if not chunks:
        return []
    model = embedding_model or E5EmbeddingModel(model_name)
    return semantic_search_chunks(
        query,
        chunks,
        model,
        limit=limit,
    )


def hybrid_search_page_data(
    page_data_path: Path,
    query: str,
    chunk_size: int = 1000,
    overlap: int = 100,
    limit: int = 5,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    embedding_model: EmbeddingModel | None = None,
    scope: ReadingScope | None = None,
) -> list[dict[str, int | float | str]]:
    chunks = _load_chunks(page_data_path, chunk_size, overlap, scope)
    if not chunks:
        return []
    model = embedding_model or E5EmbeddingModel(model_name)
    return hybrid_search_chunks(
        query,
        chunks,
        model,
        limit=limit,
    )


def _load_chunks(
    page_data_path: Path,
    chunk_size: int,
    overlap: int,
    scope: ReadingScope | None,
) -> list[dict[str, int | str]]:
    page_data = load_page_data(page_data_path)
    pages = cast(list[dict[str, int | str]], page_data["pages"])
    if scope and scope.kind == "section":
        start_page = scope.start_page or 1
        end_page = scope.end_page or start_page
        pages = [
            page
            for page in pages
            if start_page <= int(page["source_page"]) <= end_page
        ]
    return chunk_pages(pages, chunk_size=chunk_size, overlap=overlap)
