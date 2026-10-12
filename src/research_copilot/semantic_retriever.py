from collections.abc import Sequence
from collections import OrderedDict
from threading import RLock
from typing import Protocol


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_EMBEDDING_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


class EmbeddingModel(Protocol):
    def embed_query(self, query: str) -> list[float]: ...

    def embed_passages(self, passages: Sequence[str]) -> list[list[float]]: ...


class FineGrainedRelevanceModel(Protocol):
    def score_pairs(self, query: str, passages: Sequence[str]) -> list[float]: ...


class E5EmbeddingModel:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        local_files_only: bool = False,
        revision: str | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        selected_revision = revision
        if selected_revision is None and model_name == DEFAULT_EMBEDDING_MODEL:
            selected_revision = DEFAULT_EMBEDDING_REVISION
        self._model = SentenceTransformer(
            model_name,
            local_files_only=local_files_only,
            revision=selected_revision,
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


class CachedEmbeddingModel:
    """Reuse in-memory embeddings for unchanged questions and paper chunks."""

    def __init__(
        self, model: EmbeddingModel, *, max_queries: int = 128,
        max_passage_sets: int = 4,
    ) -> None:
        self.model = model
        self.max_queries = max_queries
        self.max_passage_sets = max_passage_sets
        self.query_cache: OrderedDict[str, list[float]] = OrderedDict()
        self.passage_cache: OrderedDict[tuple[str, ...], list[list[float]]] = OrderedDict()
        self._lock = RLock()

    def embed_query(self, query: str) -> list[float]:
        with self._lock:
            if query not in self.query_cache:
                self.query_cache[query] = self.model.embed_query(query)
                if len(self.query_cache) > self.max_queries:
                    self.query_cache.popitem(last=False)
            self.query_cache.move_to_end(query)
            return self.query_cache[query]

    def embed_passages(self, passages: Sequence[str]) -> list[list[float]]:
        key = tuple(passages)
        with self._lock:
            if key not in self.passage_cache:
                self.passage_cache[key] = self.model.embed_passages(passages)
                if len(self.passage_cache) > self.max_passage_sets:
                    self.passage_cache.popitem(last=False)
            self.passage_cache.move_to_end(key)
            return self.passage_cache[key]


class E5TokenAlignmentModel:
    """Experimental token-level pair scorer for the offline evidence benchmark."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        local_files_only: bool = False,
        revision: str | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        selected_revision = revision
        if selected_revision is None and model_name == DEFAULT_EMBEDDING_MODEL:
            selected_revision = DEFAULT_EMBEDDING_REVISION
        sentence_model = SentenceTransformer(
            model_name,
            local_files_only=local_files_only,
            revision=selected_revision,
        )
        transformer = sentence_model[0]
        self._tokenizer = transformer.tokenizer
        self._model = transformer.auto_model
        self._max_length = sentence_model.max_seq_length
        self._device = next(self._model.parameters()).device

    def score_pairs(self, query: str, passages: Sequence[str]) -> list[float]:
        if not query.strip() or not passages:
            return []

        import torch
        import torch.nn.functional as functional

        query_tokens = self._tokenize([f"query: {query}"])
        passage_tokens = self._tokenize(
            [f"passage: {passage}" for passage in passages]
        )
        with torch.no_grad():
            query_output = self._model(
                input_ids=query_tokens["input_ids"],
                attention_mask=query_tokens["attention_mask"],
            ).last_hidden_state
            passage_output = self._model(
                input_ids=passage_tokens["input_ids"],
                attention_mask=passage_tokens["attention_mask"],
            ).last_hidden_state

        query_embeddings = functional.normalize(query_output[0], dim=-1)
        passage_embeddings = functional.normalize(passage_output, dim=-1)
        similarities = torch.einsum(
            "qd,bpd->bqp", query_embeddings, passage_embeddings
        )
        passage_mask = self._content_mask(passage_tokens)
        similarities = similarities.masked_fill(
            ~passage_mask[:, None, :], float("-inf")
        )
        per_query_token = similarities.max(dim=-1).values
        query_mask = self._content_mask(query_tokens)[0]
        if not bool(query_mask.any()):
            return [-1.0 for _ in passages]
        scores = per_query_token[:, query_mask].mean(dim=-1)
        return [float(score) for score in scores.cpu().tolist()]

    def _tokenize(self, texts: Sequence[str]) -> dict[str, object]:
        tokens = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_special_tokens_mask=True,
            return_tensors="pt",
        )
        return {key: value.to(self._device) for key, value in tokens.items()}

    @staticmethod
    def _content_mask(tokens: dict[str, object]):
        attention_mask = tokens["attention_mask"].bool()
        special_tokens_mask = tokens["special_tokens_mask"].bool()
        return attention_mask & ~special_tokens_mask


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
