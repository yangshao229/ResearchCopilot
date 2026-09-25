from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from research_copilot.conversation_sessions import (
    ConversationSession,
    ConversationSessionStore,
)
from research_copilot.document_service import PaperDocumentService
from research_copilot.domain import (
    PaperAnswer,
    ReadingCategory,
    ReadingContext,
    ReadingRecord,
    SearchHit,
    SearchMode,
    ScopePreference,
)
from research_copilot.paper_answer_service import (
    AnswerGenerationError,
    ModelNotConfiguredError,
    PaperAnswerService,
)
from research_copilot.paper_card_compiler import (
    PaperCardCompiler,
    PaperCardPreview,
)
from research_copilot.paper_library import (
    DEFAULT_PAPER_DIRECTORY,
    PROJECT_ROOT,
    PaperImportResult,
    PaperLibrary,
    PaperSummary,
)
from research_copilot.paper_reading_guide import PaperReadingGuide
from research_copilot.paper_search_service import PaperSearchService
from research_copilot.paper_structure import PaperStructure
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.reading_service import ReadingService

DEFAULT_PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
DEFAULT_FRONTEND_DIRECTORY = PROJECT_ROOT / "web" / "dist"
DEFAULT_HISTORY_DIRECTORY = PROJECT_ROOT / "artifacts" / "reading_history"
DEFAULT_SESSION_DIRECTORY = PROJECT_ROOT / "artifacts" / "conversations"
DEFAULT_CARD_DIRECTORY = PROJECT_ROOT / "artifacts" / "paper_cards"
class PaperSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: SearchMode = "hybrid"
    limit: int = Field(default=5, ge=1, le=10)
    session_id: str = Field(default="default", pattern=r"^[A-Za-z0-9_-]+$")
    scope_preference: ScopePreference = "auto"

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("query must contain text")
        return stripped_value

    def to_reading_context(self, paper_id: str) -> ReadingContext:
        return ReadingContext(
            paper_id=paper_id,
            session_id=self.session_id,
            query=self.query,
            search_mode=self.mode,
            scope_preference=self.scope_preference,
        )


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


def create_app(
    paper_directory: Path | None = None,
    processed_directory: Path | None = None,
    frontend_directory: Path | None = None,
    search_service: PaperSearchService | None = None,
    answer_service: PaperAnswerService | None = None,
    history_store: ReadingHistoryStore | None = None,
    session_store: ConversationSessionStore | None = None,
    card_compiler: PaperCardCompiler | None = None,
    document_service: PaperDocumentService | None = None,
    reading_service: ReadingService | None = None,
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
    documents = document_service or PaperDocumentService()
    reader = reading_service or ReadingService(
        answerer,
        history,
        sessions,
        documents,
    )

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
        expose_headers=["X-Reading-Scope"],
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
            return documents.structure(paper_path)
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
            return documents.reading_guide(paper_path)
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
        response_model=list[SearchHit],
    )
    def search_paper(
        paper_id: str,
        request: PaperSearchRequest,
        response: Response,
    ) -> list[SearchHit]:
        try:
            paper_path = library.get_paper_path(paper_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail="Paper not found.",
            ) from error

        context = request.to_reading_context(paper_id)
        results, scope = reader.search(
            paper_path,
            context,
            limit=request.limit,
        )
        response.headers["X-Reading-Scope"] = json.dumps(
            scope.model_dump(), ensure_ascii=True
        )
        return [SearchHit.model_validate(result) for result in results]

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
            return reader.answer(
                paper_path,
                paper_path.name,
                request.to_reading_context(paper_id),
                limit=request.limit,
            )
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail="Conversation session not found for this paper.",
            ) from error
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
