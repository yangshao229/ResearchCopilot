from __future__ import annotations

from pathlib import Path

from research_copilot.conversation_sessions import ConversationSessionStore
from research_copilot.document_service import PaperDocumentService
from research_copilot.domain import (
    PaperAnswer,
    ReadingAnchor,
    ReadingContext,
    ReadingScope,
    SearchHit,
)
from research_copilot.paper_answer_service import PaperAnswerService
from research_copilot.paper_question_router import (
    answer_structural_question,
    classify_paper_question,
)
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.section_scope import resolve_section_scope
from research_copilot.selection_context import (
    SelectionContextPreview,
    build_selection_context,
)


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
        selection_preview: SelectionContextPreview | None = None
        direct_evidence: list[SearchHit] | None = None
        if context.task == "translate":
            if context.anchor is None or context.anchor.source_page is None:
                raise ValueError("选区翻译必须包含原文页码和选区文本。")
            selection_preview = self.selection_context(
                pdf_path,
                context.paper_id,
                context.anchor.source_page,
                context.anchor.selected_text,
            )
            if not selection_preview.selected_text:
                raise ValueError("选区为空，无法翻译。")
            direct_evidence = [
                SearchHit(
                    source_page=selection_preview.source_page,
                    chunk_index=0,
                    text=selection_preview.selected_text,
                    score=1.0,
                )
            ]
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
                language=context.language,
                task=context.task,
                direct_evidence=direct_evidence,
                task_context=(
                    selection_preview.context_text
                    if selection_preview is not None
                    else ""
                ),
            )
        answer = answer.model_copy(
            update={"scope": scope, "language": context.language}
        )

        record = self.history_store.add_record(
            context.paper_id,
            paper_name,
            context.query,
            context.search_mode,
            answer,
            session_id=context.session_id,
            scope=scope,
            language=context.language,
            task=context.task,
            anchor=context.anchor,
            context_text=(
                selection_preview.context_text
                if selection_preview is not None
                else ""
            ),
        )
        return answer.model_copy(update={"history_id": record.id})

    def selection_context(
        self,
        pdf_path: Path,
        paper_id: str,
        source_page: int,
        selected_text: str,
    ) -> SelectionContextPreview:
        page_text = self.answer_service.search_service.page_text(
            pdf_path,
            paper_id,
            source_page,
        )
        return build_selection_context(page_text, selected_text, source_page)

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
