from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

from research_copilot.paper_answer_service import (
    AnswerGenerationError,
    ModelNotConfiguredError,
    PaperAnswer,
    PaperAnswerService,
)
from research_copilot.paper_search_service import PaperSearchService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAPER_DIRECTORY = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
DEFAULT_FRONTEND_DIRECTORY = PROJECT_ROOT / "web" / "dist"


class PaperSummary(BaseModel):
    id: str
    name: str
    relative_path: str
    page_count: int | None


class PaperSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    limit: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("query must contain text")
        return stripped_value


class PaperSearchResult(BaseModel):
    source_page: int
    chunk_index: int
    text: str
    score: float
    keyword_rank: int = 0
    keyword_score: float = 0.0
    semantic_rank: int = 0
    semantic_score: float = 0.0
    fusion_score: float = 0.0
    reference_penalty: float = 0.0
    rerank_score: float = 0.0


class PaperLibrary:
    def __init__(self, paper_directory: Path) -> None:
        self.paper_directory = paper_directory.resolve()

    def list_papers(self) -> list[PaperSummary]:
        return [self._summarize(path) for path in self._pdf_paths()]

    def get_paper_path(self, paper_id: str) -> Path:
        for path in self._pdf_paths():
            if self._paper_id(path) == paper_id:
                return path

        raise KeyError(paper_id)

    def _pdf_paths(self) -> list[Path]:
        if not self.paper_directory.exists():
            return []

        paths: list[Path] = []
        for path in self.paper_directory.rglob("*.pdf"):
            resolved_path = path.resolve()
            if resolved_path.is_file() and resolved_path.is_relative_to(
                self.paper_directory
            ):
                paths.append(resolved_path)

        return sorted(
            paths,
            key=lambda path: self._relative_path(path).lower(),
        )

    def _summarize(self, path: Path) -> PaperSummary:
        try:
            page_count: int | None = len(PdfReader(path).pages)
        except Exception:
            page_count = None

        return PaperSummary(
            id=self._paper_id(path),
            name=path.name,
            relative_path=self._relative_path(path),
            page_count=page_count,
        )

    def _paper_id(self, path: Path) -> str:
        relative_path = self._relative_path(path)
        return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self.paper_directory).as_posix()


def create_app(
    paper_directory: Path | None = None,
    processed_directory: Path | None = None,
    frontend_directory: Path | None = None,
    search_service: PaperSearchService | None = None,
    answer_service: PaperAnswerService | None = None,
) -> FastAPI:
    library = PaperLibrary(paper_directory or DEFAULT_PAPER_DIRECTORY)
    frontend_path = frontend_directory or DEFAULT_FRONTEND_DIRECTORY
    searcher = search_service or PaperSearchService(
        processed_directory or DEFAULT_PROCESSED_DIRECTORY
    )
    answerer = answer_service or PaperAnswerService(searcher)

    app = FastAPI(
        title="ResearchCopilot",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/papers", response_model=list[PaperSummary])
    def list_papers() -> list[PaperSummary]:
        return library.list_papers()

    @app.get("/api/papers/{paper_id}/file")
    def get_paper_file(paper_id: str) -> FileResponse:
        try:
            paper_path = library.get_paper_path(paper_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail="Paper not found.",
            ) from error

        return FileResponse(
            paper_path,
            media_type="application/pdf",
        )

    @app.post(
        "/api/papers/{paper_id}/search",
        response_model=list[PaperSearchResult],
    )
    def search_paper(
        paper_id: str,
        request: PaperSearchRequest,
    ) -> list[dict[str, int | float | str]]:
        try:
            paper_path = library.get_paper_path(paper_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail="Paper not found.",
            ) from error

        return searcher.search(
            paper_path,
            paper_id,
            request.query,
            request.mode,
            limit=request.limit,
        )

    @app.post(
        "/api/papers/{paper_id}/answer",
        response_model=PaperAnswer,
    )
    def answer_paper(
        paper_id: str,
        request: PaperSearchRequest,
    ) -> PaperAnswer:
        try:
            paper_path = library.get_paper_path(paper_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail="Paper not found.",
            ) from error

        try:
            return answerer.answer(
                paper_path,
                paper_id,
                request.query,
                request.mode,
                limit=request.limit,
            )
        except ModelNotConfiguredError as error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "DeepSeek API 尚未配置。请在项目根目录的 .env 中设置 "
                    "DEEPSEEK_API_KEY。"
                ),
            ) from error
        except AnswerGenerationError as error:
            raise HTTPException(
                status_code=502,
                detail=str(error),
            ) from error

    if frontend_path.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=frontend_path, html=True),
            name="frontend",
        )
    else:

        @app.get("/")
        def frontend_not_built() -> dict[str, str]:
            return {
                "message": (
                    "Frontend is not built yet. "
                    "Run `npm install` and `npm run build` in web/."
                )
            }

    return app


app = create_app()
