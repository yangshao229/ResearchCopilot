from pathlib import Path

from research_copilot.domain import ReadingScope, SearchHit, SearchMode
from research_copilot.paper_search import (
    hybrid_search_page_data,
    search_page_data,
    semantic_search_page_data,
)
from research_copilot.pdf_importer import import_pdf_to_json
from research_copilot.page_store import load_page_data
from research_copilot.paper_identity import hash_pdf
from research_copilot.semantic_retriever import (
    CachedEmbeddingModel,
    E5EmbeddingModel,
    EmbeddingModel,
)

# Backward-compatible name for older imports while the codebase moves to the
# shared domain model.
SearchResult = SearchHit


class EmbeddingModelUnavailableError(RuntimeError):
    """The optional local embedding model is not ready for offline retrieval."""


class PaperSearchService:
    def __init__(
        self,
        processed_directory: Path,
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self.processed_directory = processed_directory.resolve()
        self._embedding_model = (
            CachedEmbeddingModel(embedding_model) if embedding_model is not None else None
        )

    def search(
        self,
        pdf_path: Path,
        paper_id: str,
        query: str,
        mode: SearchMode,
        limit: int = 5,
        scope: ReadingScope | None = None,
    ) -> list[SearchHit]:
        page_data_path = self._ensure_page_data(pdf_path, paper_id)

        if mode == "keyword":
            raw_results = search_page_data(
                page_data_path,
                query,
                limit=limit,
                scope=scope,
            )
        elif mode == "semantic":
            raw_results = semantic_search_page_data(
                page_data_path,
                query,
                limit=limit,
                embedding_model=self._get_embedding_model(),
                scope=scope,
            )
        else:
            raw_results = hybrid_search_page_data(
                page_data_path,
                query,
                limit=limit,
                embedding_model=self._get_embedding_model(),
                scope=scope,
            )

        normalized_results: list[SearchHit] = []
        for result in raw_results:
            normalized_result: dict[str, int | float | str] = {
                "source_page": int(result["source_page"]),
                "chunk_index": int(result["chunk_index"]),
                "text": str(result["text"]),
                "score": float(result["score"]),
            }
            for field in (
                "keyword_rank",
                "keyword_score",
                "semantic_rank",
                "semantic_score",
                "fusion_score",
                "reference_penalty",
                "rerank_score",
            ):
                if field in result:
                    value = result[field]
                    normalized_result[field] = (
                        int(value) if field.endswith("_rank") else float(value)
                    )
            normalized_results.append(SearchHit.model_validate(normalized_result))

        return normalized_results

    def page_data_path(self, paper_id: str) -> Path:
        return self.processed_directory / f"{paper_id}.json"

    def is_page_data_verified(self, pdf_path: Path, paper_id: str) -> bool:
        """Only new, fingerprinted extraction data can carry a versioned anchor."""
        page_data = load_page_data(self._ensure_page_data(pdf_path, paper_id))
        return page_data.get("source_pdf_sha256") == hash_pdf(pdf_path)

    def page_text(self, pdf_path: Path, paper_id: str, source_page: int) -> str:
        page_data_path = self._ensure_page_data(pdf_path, paper_id)
        page_data = load_page_data(page_data_path)
        pages = page_data.get("pages", [])
        if not isinstance(pages, list):
            return ""
        for page in pages:
            if (
                isinstance(page, dict)
                and page.get("source_page") == source_page
                and isinstance(page.get("text"), str)
            ):
                return page["text"]
        return ""

    def search_library_text(
        self,
        pdf_path: Path,
        paper_id: str,
        query: str,
        limit: int = 3,
    ) -> tuple[list[dict[str, int | float | str]], bool]:
        if limit <= 0:
            return [], False

        terms = [term for term in query.casefold().split() if term]
        if not terms:
            return [], False

        page_data = load_page_data(self._ensure_page_data(pdf_path, paper_id))
        pages = page_data.get("pages", [])
        if not isinstance(pages, list):
            raise ValueError("Invalid page data: pages must be a list.")

        searchable = False
        results: list[dict[str, int | float | str]] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_text = page.get("text")
            source_page = page.get("source_page")
            if not isinstance(page_text, str) or not page_text.strip():
                continue
            if not isinstance(source_page, int) or source_page < 1:
                continue

            searchable = True
            normalized_text = " ".join(page_text.split())
            folded_text = normalized_text.casefold()
            if not all(term in folded_text for term in terms):
                continue

            score = float(sum(folded_text.count(term) for term in terms))
            first_match = min(folded_text.find(term) for term in terms)
            snippet_start = max(0, first_match - 110)
            snippet_end = min(len(normalized_text), snippet_start + 280)
            snippet = normalized_text[snippet_start:snippet_end]
            if snippet_start:
                snippet = f"…{snippet}"
            if snippet_end < len(normalized_text):
                snippet = f"{snippet}…"
            results.append(
                {
                    "source_page": source_page,
                    "text": snippet,
                    "score": score,
                }
            )

        results.sort(
            key=lambda item: (-float(item["score"]), int(item["source_page"]))
        )
        return results[:limit], searchable

    def _ensure_page_data(self, pdf_path: Path, paper_id: str) -> Path:
        page_data_path = self.page_data_path(paper_id)
        cached_fingerprint = None
        if page_data_path.exists():
            cached_fingerprint = load_page_data(page_data_path).get(
                "source_pdf_sha256"
            )
        needs_import = cached_fingerprint != hash_pdf(pdf_path)

        if needs_import:
            self.processed_directory.mkdir(parents=True, exist_ok=True)
            import_pdf_to_json(pdf_path, page_data_path)

        return page_data_path

    def _get_embedding_model(self) -> EmbeddingModel:
        if self._embedding_model is None:
            try:
                # Do not let a normal paper question trigger Hugging Face retries.
                self._embedding_model = CachedEmbeddingModel(
                    E5EmbeddingModel(local_files_only=True)
                )
            except Exception as error:
                raise EmbeddingModelUnavailableError(
                    "本地 Embedding 模型尚未缓存，无法使用语义或混合检索。"
                    "请先切换到关键词检索，或按使用说明安装模型。"
                ) from error

        return self._embedding_model
