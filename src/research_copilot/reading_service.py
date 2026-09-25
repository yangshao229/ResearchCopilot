from __future__ import annotations

from pathlib import Path

from research_copilot.conversation_sessions import ConversationSessionStore
from research_copilot.document_service import PaperDocumentService
from research_copilot.domain import PaperAnswer, ReadingContext, ReadingScope
from research_copilot.paper_answer_service import PaperAnswerService
from research_copilot.paper_question_router import (
    answer_structural_question,
    classify_paper_question,
)
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.section_scope import resolve_section_scope


class ReadingService:
    def __init__(
        self,
        answer_service: PaperAnswerService,
        history_store: ReadingHistoryStore,
        session_store: ConversationSessionStore,
        document_service: PaperDocumentService,
    ) -> None:
        self.answer_service = answer_service
        self.history_store = history_store
        self.session_store = session_store
        self.document_service = document_service

    def answer(
        self,
        pdf_path: Path,
        paper_name: str,
        context: ReadingContext,
        limit: int = 5,
    ) -> PaperAnswer:
        if not self.session_store.contains(context.paper_id, context.session_id):
            raise KeyError(context.session_id)

        answer = None
        is_content_question = classify_paper_question(context.query) == "content"
        scope = (
            resolve_section_scope(
                context.query,
                self.document_service.structure(pdf_path),
                forced_full_paper=context.scope_preference == "full_paper",
            )
            if is_content_question
            else ReadingScope()
        )
        if not is_content_question:
            answer = answer_structural_question(
                context.query,
                self.document_service.structure(pdf_path),
            )
        if answer is None:
            answer = self.answer_service.answer(
                pdf_path,
                context.paper_id,
                context.query,
                context.search_mode,
                limit=limit,
                scope=scope if scope.kind == "section" else None,
            )
        answer = answer.model_copy(update={"scope": scope})

        record = self.history_store.add_record(
            context.paper_id,
            paper_name,
            context.query,
            context.search_mode,
            answer,
            session_id=context.session_id,
            scope=scope,
        )
        return answer.model_copy(update={"history_id": record.id})

    def resolve_scope(
        self,
        pdf_path: Path,
        context: ReadingContext,
    ) -> ReadingScope:
        return resolve_section_scope(
            context.query,
            self.document_service.structure(pdf_path),
            forced_full_paper=context.scope_preference == "full_paper",
        )

    def search(
        self,
        pdf_path: Path,
        context: ReadingContext,
        limit: int = 5,
    ) -> tuple[list[dict[str, object]], ReadingScope]:
        scope = self.resolve_scope(pdf_path, context)
        if scope.kind == "section":
            results = self.answer_service.search_service.search(
                pdf_path,
                context.paper_id,
                context.query,
                context.search_mode,
                limit=limit,
                scope=scope,
            )
        else:
            results = self.answer_service.search_service.search(
                pdf_path,
                context.paper_id,
                context.query,
                context.search_mode,
                limit=limit,
            )
        return [
            result.model_dump() if hasattr(result, "model_dump") else dict(result)
            for result in results
        ], scope
