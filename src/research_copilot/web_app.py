from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Literal
from urllib.parse import unquote
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

from research_copilot.conversation_sessions import (
    ConversationSession,
    ConversationSessionStore,
)
from research_copilot.paper_answer_service import (
    AnswerGenerationError,
    ModelNotConfiguredError,
    PaperAnswer,
    PaperAnswerService,
)
from research_copilot.paper_card_compiler import (
    PaperCardCompiler,
    PaperCardPreview,
)
from research_copilot.paper_question_router import (
    answer_structural_question,
    classify_paper_question,
)
from research_copilot.paper_reading_guide import (
    PaperReadingGuide,
    build_reading_guide,
)
from research_copilot.paper_search_service import PaperSearchService
from research_copilot.paper_structure import PaperStructure, extract_paper_structure
from research_copilot.reading_history import (
    ReadingCategory,
    ReadingHistoryStore,
    ReadingRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAPER_DIRECTORY = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
DEFAULT_FRONTEND_DIRECTORY = PROJECT_ROOT / "web" / "dist"
DEFAULT_HISTORY_DIRECTORY = PROJECT_ROOT / "artifacts" / "reading_history"
DEFAULT_SESSION_DIRECTORY = PROJECT_ROOT / "artifacts" / "conversations"
DEFAULT_CARD_DIRECTORY = PROJECT_ROOT / "artifacts" / "paper_cards"
MAX_PDF_UPLOAD_BYTES = 100 * 1024 * 1024


class PaperSummary(BaseModel):
    id: str
    name: str
    relative_path: str
    page_count: int | None


class PaperImportResult(BaseModel):
    paper: PaperSummary
    imported: bool
    message: str


class PaperSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    limit: int = Field(default=5, ge=1, le=10)
    session_id: str = Field(default="default", pattern=r"^[A-Za-z0-9_-]+$")

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


class ReadingRecordUpdate(BaseModel):
    confirmed: bool
    personal_note: str = Field(default="", max_length=5000)
    category: ReadingCategory = "unclassified"


class ConversationSessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def title_must_contain_text(cls, value: str) -> str:
        cleaned_value = " ".join(value.strip().split())
        if not cleaned_value:
            raise ValueError("title must contain text")
        return cleaned_value


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

    def import_pdf(self, filename: str, content: bytes) -> PaperImportResult:
        if not content or len(content) > MAX_PDF_UPLOAD_BYTES:
            raise ValueError("PDF 文件为空或超过 100 MB 大小限制。")

        safe_name = Path(filename.replace("\\", "/")).name.strip()
        if not safe_name.lower().endswith(".pdf"):
            raise ValueError("只能导入扩展名为 .pdf 的文件。")

        try:
            PdfReader(BytesIO(content))
        except Exception as error:
            raise ValueError("文件不是有效的 PDF，或 PDF 已损坏。") from error

        digest = hashlib.sha256(content).hexdigest()
        for existing_path in self._pdf_paths():
            if self._file_digest(existing_path) == digest:
                return PaperImportResult(
                    paper=self._summarize(existing_path),
                    imported=False,
                    message="这篇论文已经在本地资料库中。",
                )

        self.paper_directory.mkdir(parents=True, exist_ok=True)
        output_path = self._available_path(safe_name)
        temporary_path = self.paper_directory / f".{uuid4().hex}.uploading"
        temporary_path.write_bytes(content)
        temporary_path.replace(output_path)
        return PaperImportResult(
            paper=self._summarize(output_path),
            imported=True,
            message="PDF 已导入本地资料库。",
        )

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

    @staticmethod
    def _file_digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            for block in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _available_path(self, filename: str) -> Path:
        candidate = self.paper_directory / filename
        suffix_number = 2
        while candidate.exists():
            candidate = self.paper_directory / (
                f"{Path(filename).stem}-{suffix_number}{Path(filename).suffix}"
            )
            suffix_number += 1
        return candidate


def create_app(
    paper_directory: Path | None = None,
    processed_directory: Path | None = None,
    frontend_directory: Path | None = None,
    search_service: PaperSearchService | None = None,
    answer_service: PaperAnswerService | None = None,
    history_store: ReadingHistoryStore | None = None,
    session_store: ConversationSessionStore | None = None,
    card_compiler: PaperCardCompiler | None = None,
) -> FastAPI:
    library = PaperLibrary(paper_directory or DEFAULT_PAPER_DIRECTORY)
    frontend_path = frontend_directory or DEFAULT_FRONTEND_DIRECTORY
    searcher = search_service or PaperSearchService(
        processed_directory or DEFAULT_PROCESSED_DIRECTORY
    )
    answerer = answer_service or PaperAnswerService(searcher)
    history = history_store or ReadingHistoryStore(DEFAULT_HISTORY_DIRECTORY)
    session_directory = (
        history.root_directory.parent / "conversations"
        if history_store is not None
        else DEFAULT_SESSION_DIRECTORY
    )
    sessions = session_store or ConversationSessionStore(session_directory)
    cards = card_compiler or PaperCardCompiler(DEFAULT_CARD_DIRECTORY)

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
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/papers", response_model=list[PaperSummary])
    def list_papers() -> list[PaperSummary]:
        return library.list_papers()

    @app.post("/api/papers/import", response_model=PaperImportResult)
    async def import_paper(request: Request) -> PaperImportResult:
        encoded_filename = request.headers.get("x-pdf-filename", "")
        if not encoded_filename:
            raise HTTPException(status_code=400, detail="缺少 PDF 文件名。")

        content = await request.body()
        try:
            return library.import_pdf(unquote(encoded_filename), content)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

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

    @app.get(
        "/api/papers/{paper_id}/structure",
        response_model=PaperStructure,
    )
    def get_paper_structure(paper_id: str) -> PaperStructure:
        try:
            paper_path = library.get_paper_path(paper_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail="Paper not found.",
            ) from error

        try:
            return extract_paper_structure(paper_path)
        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail="无法解析这篇 PDF 的目录结构。",
            ) from error

    @app.get(
        "/api/papers/{paper_id}/guide",
        response_model=PaperReadingGuide,
    )
    def get_paper_guide(paper_id: str) -> PaperReadingGuide:
        try:
            paper_path = library.get_paper_path(paper_id)
            return build_reading_guide(extract_paper_structure(paper_path))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Paper not found.") from error
        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail="无法为这篇 PDF 生成阅读路线。",
            ) from error

    @app.get(
        "/api/papers/{paper_id}/sessions",
        response_model=list[ConversationSession],
    )
    def list_conversation_sessions(paper_id: str) -> list[ConversationSession]:
        try:
            library.get_paper_path(paper_id)
            return sessions.list_sessions(paper_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Paper not found.") from error

    @app.post(
        "/api/papers/{paper_id}/sessions",
        response_model=ConversationSession,
    )
    def create_conversation_session(
        paper_id: str,
        request: ConversationSessionCreate,
    ) -> ConversationSession:
        try:
            library.get_paper_path(paper_id)
            return sessions.create_session(paper_id, request.title)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Paper not found.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

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
            if not sessions.contains(paper_id, request.session_id):
                raise HTTPException(
                    status_code=404,
                    detail="Conversation session not found for this paper.",
                )
            answer = None
            if classify_paper_question(request.query) != "content":
                answer = answer_structural_question(
                    request.query,
                    extract_paper_structure(paper_path),
                )
            if answer is None:
                answer = answerer.answer(
                    paper_path,
                    paper_id,
                    request.query,
                    request.mode,
                    limit=request.limit,
                )
            record = history.add_record(
                paper_id,
                paper_path.name,
                request.query,
                request.mode,
                answer,
                session_id=request.session_id,
            )
            return answer.model_copy(update={"history_id": record.id})
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

    @app.get(
        "/api/papers/{paper_id}/history",
        response_model=list[ReadingRecord],
    )
    def list_reading_history(
        paper_id: str,
        session_id: str | None = None,
    ) -> list[ReadingRecord]:
        try:
            library.get_paper_path(paper_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Paper not found.") from error
        if session_id is not None and not sessions.contains(paper_id, session_id):
            raise HTTPException(
                status_code=404,
                detail="Conversation session not found for this paper.",
            )
        return history.list_records(paper_id, session_id=session_id)

    @app.patch(
        "/api/papers/{paper_id}/history/{record_id}",
        response_model=ReadingRecord,
    )
    def update_reading_history(
        paper_id: str,
        record_id: str,
        request: ReadingRecordUpdate,
    ) -> ReadingRecord:
        try:
            library.get_paper_path(paper_id)
            return history.update_record(
                paper_id,
                record_id,
                request.confirmed,
                request.personal_note,
                request.category,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Record not found.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/papers/{paper_id}/history/{record_id}/export")
    def export_reading_history(paper_id: str, record_id: str) -> FileResponse:
        try:
            library.get_paper_path(paper_id)
            export_path = history.export_record(paper_id, record_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Record not found.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return FileResponse(
            export_path,
            media_type="text/markdown; charset=utf-8",
            filename=export_path.name,
        )

    @app.get(
        "/api/papers/{paper_id}/card/preview",
        response_model=PaperCardPreview,
    )
    def preview_paper_card(paper_id: str) -> PaperCardPreview:
        try:
            paper_path = library.get_paper_path(paper_id)
            return cards.preview(
                paper_id,
                paper_path.name,
                history.list_records(paper_id),
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Paper not found.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/papers/{paper_id}/card/export")
    def export_paper_card(
        paper_id: str,
        new_version: bool = False,
    ) -> FileResponse:
        try:
            paper_path = library.get_paper_path(paper_id)
            output_path = cards.export(
                paper_id,
                paper_path.name,
                history.list_records(paper_id),
                new_version=new_version,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Paper not found.") from error
        except (ValueError, FileExistsError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return FileResponse(
            output_path,
            media_type="text/markdown; charset=utf-8",
            filename=output_path.name,
        )

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
