from __future__ import annotations

from pathlib import Path

from research_copilot.conversation_sessions import ConversationSessionStore
from research_copilot.document_service import PaperDocumentService
from research_copilot.domain import PaperAnswer, ReadingContext
from research_copilot.paper_answer_service import PaperAnswerService
from research_copilot.paper_question_router import (
    answer_structural_question,
    classify_paper_question,
)
from research_copilot.reading_history import ReadingHistoryStore


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
        if classify_paper_question(context.query) != "content":
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
            )

        record = self.history_store.add_record(
            context.paper_id,
            paper_name,
            context.query,
            context.search_mode,
            answer,
            session_id=context.session_id,
        )
        return answer.model_copy(update={"history_id": record.id})
