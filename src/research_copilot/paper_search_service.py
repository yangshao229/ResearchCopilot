from pathlib import Path
from typing import Literal

from research_copilot.paper_search import (
    hybrid_search_page_data,
    search_page_data,
    semantic_search_page_data,
)
from research_copilot.pdf_importer import import_pdf_to_json
from research_copilot.semantic_retriever import (
    E5EmbeddingModel,
    EmbeddingModel,
)

SearchMode = Literal["keyword", "semantic", "hybrid"]
SearchResult = dict[str, int | float | str]


class PaperSearchService:
    def __init__(
        self,
        processed_directory: Path,
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self.processed_directory = processed_directory.resolve()
        self._embedding_model = embedding_model

    def search(
        self,
        pdf_path: Path,
        paper_id: str,
        query: str,
        mode: SearchMode,
        limit: int = 5,
    ) -> list[SearchResult]:
        page_data_path = self._ensure_page_data(pdf_path, paper_id)

        if mode == "keyword":
            raw_results = search_page_data(
                page_data_path,
                query,
                limit=limit,
            )
        elif mode == "semantic":
            raw_results = semantic_search_page_data(
                page_data_path,
                query,
                limit=limit,
                embedding_model=self._get_embedding_model(),
            )
        else:
            raw_results = hybrid_search_page_data(
                page_data_path,
                query,
                limit=limit,
                embedding_model=self._get_embedding_model(),
            )

        normalized_results: list[SearchResult] = []
        for result in raw_results:
            normalized_result: SearchResult = {
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
            normalized_results.append(normalized_result)

        return normalized_results

    def page_data_path(self, paper_id: str) -> Path:
        return self.processed_directory / f"{paper_id}.json"

    def _ensure_page_data(self, pdf_path: Path, paper_id: str) -> Path:
        page_data_path = self.page_data_path(paper_id)
        needs_import = (
            not page_data_path.exists()
            or page_data_path.stat().st_mtime < pdf_path.stat().st_mtime
        )

        if needs_import:
            self.processed_directory.mkdir(parents=True, exist_ok=True)
            import_pdf_to_json(pdf_path, page_data_path)

        return page_data_path

    def _get_embedding_model(self) -> EmbeddingModel:
        if self._embedding_model is None:
            self._embedding_model = E5EmbeddingModel()

        return self._embedding_model
