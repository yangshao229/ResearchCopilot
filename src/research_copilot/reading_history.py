from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from research_copilot.paper_answer_service import AnswerCitation, PaperAnswer
from research_copilot.paper_search_service import SearchMode

ReadingCategory = Literal[
    "unclassified",
    "summary",
    "research_problem",
    "method",
    "experiments",
    "contributions",
    "limitations",
    "open_questions",
]


class ReadingRecord(BaseModel):
    id: str
    paper_id: str
    paper_name: str
    created_at: str
    question: str
    search_mode: SearchMode
    answer: str
    explanation: str
    citations: list[AnswerCitation]
    insufficient_evidence: bool
    uncertainty: str
    provider: str
    model: str
    confirmed: bool = False
    personal_note: str = ""
    category: ReadingCategory = "unclassified"


class ReadingHistoryStore:
    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory.resolve()
        self.export_directory = self.root_directory / "exports"

    def list_records(self, paper_id: str) -> list[ReadingRecord]:
        path = self._history_path(paper_id)
        if not path.exists():
            return []

        with path.open("r", encoding="utf-8") as history_file:
            raw_records = json.load(history_file)
        return [ReadingRecord.model_validate(record) for record in raw_records]

    def add_record(
        self,
        paper_id: str,
        paper_name: str,
        question: str,
        search_mode: SearchMode,
        answer: PaperAnswer,
    ) -> ReadingRecord:
        record = ReadingRecord(
            id=uuid4().hex,
            paper_id=paper_id,
            paper_name=paper_name,
            created_at=datetime.now(UTC).isoformat(),
            question=question,
            search_mode=search_mode,
            answer=answer.answer,
            explanation=answer.explanation,
            citations=answer.citations,
            insufficient_evidence=answer.insufficient_evidence,
            uncertainty=answer.uncertainty,
            provider=answer.provider,
            model=answer.model,
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
        if not re.fullmatch(r"[A-Za-z0-9_-]+", paper_id):
            raise ValueError("Invalid paper id.")
        return self.root_directory / f"{paper_id}.json"

    def _write_records(
        self,
        paper_id: str,
        records: list[ReadingRecord],
    ) -> None:
        self.root_directory.mkdir(parents=True, exist_ok=True)
        path = self._history_path(paper_id)
        temporary_path = path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(
                [record.model_dump(mode="json") for record in records],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)

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
        return (
            "---\n"
            f"source_pdf: {json.dumps(record.paper_name, ensure_ascii=False)}\n"
            f"question_id: {record.id}\n"
            f"created_at: {record.created_at}\n"
            "review_status: confirmed\n"
            f"model: {json.dumps(record.model, ensure_ascii=False)}\n"
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
