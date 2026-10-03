from collections.abc import Sequence
from typing import Protocol


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


class EmbeddingModel(Protocol):
    def embed_query(self, query: str) -> list[float]: ...

    def embed_passages(self, passages: Sequence[str]) -> list[list[float]]: ...


class E5EmbeddingModel:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        local_files_only: bool = False,
        revision: str | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            model_name,
            local_files_only=local_files_only,
            revision=revision,
        )

    def embed_query(self, query: str) -> list[float]:
        embedding = self._model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
        )[0]
        return embedding.tolist()

    def embed_passages(self, passages: Sequence[str]) -> list[list[float]]:
        embeddings = self._model.encode(
            [f"passage: {passage}" for passage in passages],
            normalize_embeddings=True,
        )
        return [embedding.tolist() for embedding in embeddings]


def semantic_search_chunks(
    query: str,
    chunks: list[dict[str, int | str]],
    embedding_model: EmbeddingModel,
    limit: int = 5,
) -> list[dict[str, int | float | str]]:
    if limit <= 0 or not query.strip() or not chunks:
        return []

    query_embedding = embedding_model.embed_query(query)
    passage_embeddings = embedding_model.embed_passages(
        [str(chunk["text"]) for chunk in chunks]
    )

    if len(passage_embeddings) != len(chunks):
        raise ValueError("embedding count must match chunk count")

    results: list[dict[str, int | float | str]] = []
    for chunk, passage_embedding in zip(chunks, passage_embeddings, strict=True):
        if len(query_embedding) != len(passage_embedding):
            raise ValueError("query and passage embeddings must have equal dimensions")

        score = sum(
            query_value * passage_value
            for query_value, passage_value in zip(
                query_embedding,
                passage_embedding,
                strict=True,
            )
        )
        results.append({**chunk, "score": score})

    results.sort(
        key=lambda item: (
            -float(item["score"]),
            int(item["source_page"]),
            int(item["chunk_index"]),
        )
    )
    return results[:limit]
