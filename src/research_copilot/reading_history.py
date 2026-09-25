from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from research_copilot.domain import (
    LanguagePolicy,
    PaperAnswer,
    ReadingCategory,
    ReadingAnchor,
    ReadingRecord,
    ReadingScope,
    SearchMode,
    ReadingTask,
)
from research_copilot.storage import (
    atomic_write_json,
    read_json,
    validated_json_path,
)


class ReadingHistoryStore:
    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory.resolve()
        self.export_directory = self.root_directory / "exports"
        self._lock = RLock()

    def list_records(
        self,
        paper_id: str,
        session_id: str | None = None,
    ) -> list[ReadingRecord]:
        with self._lock:
            raw_records = read_json(self._history_path(paper_id), [])
            records = [
                ReadingRecord.model_validate(record) for record in raw_records
            ]
            if session_id is None:
                return records
            return [
                record for record in records if record.session_id == session_id
            ]

    def add_record(
        self,
        paper_id: str,
        paper_name: str,
        question: str,
        search_mode: SearchMode,
        answer: PaperAnswer,
        session_id: str = "default",
        scope: ReadingScope | None = None,
        language: LanguagePolicy | None = None,
        task: ReadingTask = "question",
        anchor: ReadingAnchor | None = None,
        context_text: str = "",
    ) -> ReadingRecord:
        with self._lock:
            record = ReadingRecord(
                id=uuid4().hex,
                paper_id=paper_id,
                paper_name=paper_name,
                created_at=datetime.now(UTC).isoformat(),
                question=question,
                task=task,
                session_id=session_id,
                anchor=anchor,
                context_text=context_text,
                search_mode=search_mode,
                answer=answer.answer,
                explanation=answer.explanation,
                citations=answer.citations,
                insufficient_evidence=answer.insufficient_evidence,
                uncertainty=answer.uncertainty,
                provider=answer.provider,
                model=answer.model,
                scope=scope or answer.scope,
                language=language or answer.language,
            )
            records = self.list_records(paper_id)
            records.insert(0, record)
            self._write_records(paper_id, records)
            return record

    def update_record(
        self,
        paper_id: str,
        record_id: str,
        confirmed: bool,
        personal_note: str,
        category: ReadingCategory = "unclassified",
    ) -> ReadingRecord:
        with self._lock:
            cleaned_note = personal_note.strip()
            if confirmed and not cleaned_note:
                raise ValueError(
                    "加入论文卡片前，请先写下核对原文后的个人理解。"
                )
            if confirmed and category == "unclassified":
                raise ValueError("加入论文卡片前，请先选择记录所属栏目。")

            records = self.list_records(paper_id)
            for index, record in enumerate(records):
                if record.id != record_id:
                    continue

                updated_record = record.model_copy(
                    update={
                        "confirmed": confirmed,
                        "personal_note": cleaned_note,
                        "category": category,
                    }
                )
                records[index] = updated_record
                self._write_records(paper_id, records)
                return updated_record

            raise KeyError(record_id)

    def export_record(self, paper_id: str, record_id: str) -> Path:
        record = self._get_record(paper_id, record_id)
        if not record.confirmed:
            raise ValueError("Only confirmed reading records can be exported.")

        self.export_directory.mkdir(parents=True, exist_ok=True)
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(record.paper_name).stem)
        output_path = self.export_directory / f"{safe_stem}-{record.id[:8]}.md"
        output_path.write_text(self._build_markdown(record), encoding="utf-8")
        return output_path

    def _get_record(self, paper_id: str, record_id: str) -> ReadingRecord:
        for record in self.list_records(paper_id):
            if record.id == record_id:
                return record
        raise KeyError(record_id)

    def _history_path(self, paper_id: str) -> Path:
        return validated_json_path(self.root_directory, paper_id)

    def _write_records(
        self,
        paper_id: str,
        records: list[ReadingRecord],
    ) -> None:
        atomic_write_json(
            self._history_path(paper_id),
            [record.model_dump(mode="json") for record in records],
        )

    @staticmethod
    def _build_markdown(record: ReadingRecord) -> str:
        citation_sections = "\n\n".join(
            (
                f"### [E{citation.evidence_id}] PDF 第 {citation.source_page} 页\n\n"
                f"> {citation.quote.replace(chr(10), ' ')}"
            )
            for citation in record.citations
        ) or "无已验证引用。"
        note = record.personal_note or "（尚未填写个人备注）"
        scope_note = record.scope.note or "全文"
        return (
            "---\n"
            f"source_pdf: {json.dumps(record.paper_name, ensure_ascii=False)}\n"
            f"question_id: {record.id}\n"
            f"created_at: {record.created_at}\n"
            f"task: {record.task}\n"
            f"source_page: {record.anchor.source_page if record.anchor else ''}\n"
            "review_status: confirmed\n"
            f"model: {json.dumps(record.model, ensure_ascii=False)}\n"
            f"reading_scope: {json.dumps(scope_note, ensure_ascii=False)}\n"
            f"explanation_language: {record.language.explanation_language}\n"
            f"translation_target: {record.language.translation_target}\n"
            f"terminology_policy: {record.language.terminology_policy}\n"
            "---\n\n"
            f"# {record.question}\n\n"
            "## AI 回答\n\n"
            f"{record.answer}\n\n"
            "## 解释\n\n"
            f"{record.explanation}\n\n"
            "## 已验证原文引用\n\n"
            f"{citation_sections}\n\n"
            "## 我的理解\n\n"
            f"{note}\n\n"
            "## 不确定性\n\n"
            f"{record.uncertainty or '无额外说明。'}\n"
        )
