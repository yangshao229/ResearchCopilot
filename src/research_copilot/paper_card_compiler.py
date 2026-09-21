from __future__ import annotations

import json
import re
from difflib import unified_diff
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from research_copilot.reading_history import ReadingCategory, ReadingRecord


class PaperCardPreview(BaseModel):
    paper_id: str
    paper_name: str
    confirmed_record_count: int
    markdown: str
    output_filename: str
    existing_card: bool
    diff: str


SECTION_LABELS: list[tuple[ReadingCategory, str]] = [
    ("summary", "一句话结论"),
    ("research_problem", "研究问题"),
    ("method", "方法"),
    ("experiments", "实验"),
    ("contributions", "贡献"),
    ("limitations", "局限"),
    ("open_questions", "未解决问题"),
    ("unclassified", "待分类记录"),
]


class PaperCardCompiler:
    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory.resolve()

    def preview(
        self,
        paper_id: str,
        paper_name: str,
        records: list[ReadingRecord],
    ) -> PaperCardPreview:
        confirmed_records = [record for record in records if record.confirmed]
        if len(confirmed_records) < 2:
            raise ValueError(
                "至少需要两条已人工确认的阅读记录才能生成论文卡片。"
            )

        markdown = self._build_markdown(
            paper_id,
            paper_name,
            confirmed_records,
        )
        output_path = self._primary_output_path(paper_name)
        existing_markdown = (
            output_path.read_text(encoding="utf-8")
            if output_path.exists()
            else ""
        )
        difference = (
            "".join(
                unified_diff(
                    existing_markdown.splitlines(keepends=True),
                    markdown.splitlines(keepends=True),
                    fromfile=f"existing/{output_path.name}",
                    tofile=f"preview/{output_path.name}",
                )
            )
            if existing_markdown
            else ""
        )
        return PaperCardPreview(
            paper_id=paper_id,
            paper_name=paper_name,
            confirmed_record_count=len(confirmed_records),
            markdown=markdown,
            output_filename=output_path.name,
            existing_card=output_path.exists(),
            diff=difference,
        )

    def export(
        self,
        paper_id: str,
        paper_name: str,
        records: list[ReadingRecord],
        new_version: bool = False,
    ) -> Path:
        preview = self.preview(paper_id, paper_name, records)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        output_path = self._primary_output_path(paper_name)
        if output_path.exists():
            if not new_version:
                raise FileExistsError(
                    f"拒绝覆盖已有论文卡片：{output_path.name}"
                )
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
            output_path = output_path.with_name(
                f"{output_path.stem}-{timestamp}.md"
            )

        output_path.write_text(preview.markdown, encoding="utf-8")
        return output_path

    def _primary_output_path(self, paper_name: str) -> Path:
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(paper_name).stem)
        return self.output_directory / f"{safe_stem}.md"

    @classmethod
    def _build_markdown(
        cls,
        paper_id: str,
        paper_name: str,
        records: list[ReadingRecord],
    ) -> str:
        created_at = datetime.now(UTC).isoformat()
        sections = "\n\n".join(
            cls._build_section(category, label, records)
            for category, label in SECTION_LABELS
        )
        return (
            "---\n"
            f"source_pdf: {json.dumps(paper_name, ensure_ascii=False)}\n"
            f"paper_id: {paper_id}\n"
            f"created_at: {created_at}\n"
            "review_status: confirmed\n"
            f"confirmed_records: {len(records)}\n"
            "---\n\n"
            f"# {Path(paper_name).stem}\n\n"
            "> 本卡片仅汇总用户已确认的阅读记录；空白部分保留为待补充项。\n\n"
            f"{sections}\n"
        )

    @classmethod
    def _build_section(
        cls,
        category: ReadingCategory,
        label: str,
        records: list[ReadingRecord],
    ) -> str:
        matching_records = [
            record for record in records if record.category == category
        ]
        if not matching_records:
            return f"## {label}\n\n> TODO：尚无已确认记录。"

        entries = "\n\n".join(cls._build_entry(record) for record in matching_records)
        return f"## {label}\n\n{entries}"

    @staticmethod
    def _build_entry(record: ReadingRecord) -> str:
        user_conclusion = record.personal_note or record.answer
        citations = "\n".join(
            (
                f"- [PDF 第 {citation.source_page} 页] "
                f"{citation.quote.replace(chr(10), ' ')}"
            )
            for citation in record.citations
        ) or "- 无已验证引用"
        ai_context = (
            f"\n\n<details>\n<summary>AI 辅助回答</summary>\n\n"
            f"{record.answer}\n\n</details>"
            if record.personal_note
            else ""
        )
        return (
            f"### {record.question}\n\n"
            f"{user_conclusion}{ai_context}\n\n"
            f"**原文依据**\n\n{citations}\n\n"
            f"<!-- reading-record: {record.id} -->"
        )
