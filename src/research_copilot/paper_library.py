from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field
from pypdf import PdfReader

from research_copilot.paper_identity import PaperIdentityStore, PaperVersionStatus, hash_pdf
from research_copilot.domain import SourceDocumentRef
from research_copilot.source_language import (
    DetectedSourceLanguage,
    detect_source_language,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAPER_DIRECTORY = PROJECT_ROOT / "data" / "raw"
MAX_PDF_UPLOAD_BYTES = 100 * 1024 * 1024


class PaperSummary(BaseModel):
    id: str
    paper_uid: str | None = None
    pdf_sha256: str | None = None
    pdf_version_status: PaperVersionStatus | None = None
    name: str
    relative_path: str
    page_count: int | None
    detected_source_language: DetectedSourceLanguage = "unknown"
    collection_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class PaperImportResult(BaseModel):
    paper: PaperSummary
    imported: bool
    message: str


class PaperLibrary:
    def __init__(
        self,
        paper_directory: Path,
        identity_store: PaperIdentityStore | None = None,
    ) -> None:
        self.paper_directory = paper_directory.resolve()
        self.identity_store = identity_store

    def list_papers(self) -> list[PaperSummary]:
        return [self._summarize(path) for path in self._pdf_paths()]

    def get_paper_path(self, paper_id: str) -> Path:
        for path in self._pdf_paths():
            if self._paper_id(path) == paper_id:
                return path
        raise KeyError(paper_id)

    def source_document(self, paper_id: str) -> SourceDocumentRef | None:
        """Resolve the exact local PDF version without parsing every page."""
        path = self.get_paper_path(paper_id)
        if self.identity_store is None:
            return None
        identity = self.identity_store.resolve(
            legacy_paper_id=paper_id,
            relative_path=self._relative_path(path),
            pdf_sha256=self._file_digest(path),
        )
        return SourceDocumentRef(
            paper_uid=identity.paper_uid,
            pdf_sha256=identity.pdf_sha256,
        )

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

        paths = [
            resolved_path
            for path in self.paper_directory.rglob("*.pdf")
            if (resolved_path := path.resolve()).is_file()
            and resolved_path.is_relative_to(self.paper_directory)
        ]
        return sorted(paths, key=lambda path: self._relative_path(path).lower())

    def _summarize(self, path: Path) -> PaperSummary:
        try:
            reader = PdfReader(path)
            page_count: int | None = len(reader.pages)
            page_texts: list[str] = []
            for page in reader.pages[:5]:
                try:
                    page_texts.append(page.extract_text() or "")
                except Exception:
                    continue
            detected_language = detect_source_language(page_texts)
        except Exception:
            page_count = None
            detected_language = "unknown"
        paper_id = self._paper_id(path)
        relative_path = self._relative_path(path)
        identity = None
        if self.identity_store is not None:
            identity = self.identity_store.resolve(
                legacy_paper_id=paper_id,
                relative_path=relative_path,
                pdf_sha256=self._file_digest(path),
            )
        return PaperSummary(
            id=paper_id,
            paper_uid=identity.paper_uid if identity else None,
            pdf_sha256=identity.pdf_sha256 if identity else None,
            pdf_version_status=identity.version_status if identity else None,
            name=path.name,
            relative_path=relative_path,
            page_count=page_count,
            detected_source_language=detected_language,
        )

    def _paper_id(self, path: Path) -> str:
        return hashlib.sha256(
            self._relative_path(path).encode("utf-8")
        ).hexdigest()[:16]

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self.paper_directory).as_posix()

    @staticmethod
    def _file_digest(path: Path) -> str:
        return hash_pdf(path)

    def _available_path(self, filename: str) -> Path:
        candidate = self.paper_directory / filename
        suffix_number = 2
        while candidate.exists():
            candidate = self.paper_directory / (
                f"{Path(filename).stem}-{suffix_number}{Path(filename).suffix}"
            )
            suffix_number += 1
        return candidate
