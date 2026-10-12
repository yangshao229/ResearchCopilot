from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from research_copilot.storage import atomic_write_json, read_json


PaperVersionStatus = Literal["current", "changed"]


def hash_pdf(path: Path) -> str:
    """Hash a PDF without loading the whole file into memory."""
    digest = sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class PaperIdentityRecord(BaseModel):
    schema_version: int = 1
    paper_uid: str = Field(pattern=r"^paper-[0-9a-f]{32}$")
    pdf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    legacy_paper_ids: list[str] = Field(default_factory=list)
    relative_paths: list[str] = Field(default_factory=list)


class PaperIdentityMatch(BaseModel):
    paper_uid: str
    pdf_sha256: str
    registered_pdf_sha256: str
    version_status: PaperVersionStatus


class PaperIdentityStore:
    """Persist path-independent paper identities without rewriting PDF files."""

    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory
        self.index_path = root_directory / "index.json"
        self._lock = RLock()

    def resolve(
        self,
        *,
        legacy_paper_id: str,
        relative_path: str,
        pdf_sha256: str,
    ) -> PaperIdentityMatch:
        with self._lock:
            records = self._load_records()
            record = self._find_record(
                records,
                legacy_paper_id=legacy_paper_id,
                relative_path=relative_path,
                pdf_sha256=pdf_sha256,
            )
            if record is None:
                record = PaperIdentityRecord(
                    paper_uid=f"paper-{uuid4().hex}",
                    pdf_sha256=pdf_sha256,
                    legacy_paper_ids=[legacy_paper_id],
                    relative_paths=[relative_path],
                )
                records.append(record)
                self._save_records(records)
            else:
                changed = False
                if legacy_paper_id not in record.legacy_paper_ids:
                    record.legacy_paper_ids.append(legacy_paper_id)
                    changed = True
                if relative_path not in record.relative_paths:
                    record.relative_paths.append(relative_path)
                    changed = True
                if changed:
                    self._save_records(records)

            return PaperIdentityMatch(
                paper_uid=record.paper_uid,
                pdf_sha256=pdf_sha256,
                registered_pdf_sha256=record.pdf_sha256,
                version_status=(
                    "current" if record.pdf_sha256 == pdf_sha256 else "changed"
                ),
            )

    def _load_records(self) -> list[PaperIdentityRecord]:
        raw_records = read_json(self.index_path, [])
        if not isinstance(raw_records, list):
            raise ValueError("Paper identity index must contain a list.")
        records = [PaperIdentityRecord.model_validate(item) for item in raw_records]
        self._validate_unique(records)
        return records

    @staticmethod
    def _find_record(
        records: list[PaperIdentityRecord],
        *,
        legacy_paper_id: str,
        relative_path: str,
        pdf_sha256: str,
    ) -> PaperIdentityRecord | None:
        alias_matches = [
            record
            for record in records
            if legacy_paper_id in record.legacy_paper_ids
            or relative_path in record.relative_paths
        ]
        if len(alias_matches) > 1:
            raise ValueError("Paper identity aliases resolve to multiple records.")
        if alias_matches:
            return alias_matches[0]

        digest_matches = [
            record for record in records if record.pdf_sha256 == pdf_sha256
        ]
        if len(digest_matches) > 1:
            raise ValueError("PDF fingerprint resolves to multiple paper identities.")
        return digest_matches[0] if digest_matches else None

    @staticmethod
    def _validate_unique(records: list[PaperIdentityRecord]) -> None:
        paper_uids: set[str] = set()
        legacy_ids: set[str] = set()
        relative_paths: set[str] = set()
        for record in records:
            if record.paper_uid in paper_uids:
                raise ValueError("Duplicate paper UID in identity index.")
            paper_uids.add(record.paper_uid)
            for legacy_id in record.legacy_paper_ids:
                if legacy_id in legacy_ids:
                    raise ValueError("Duplicate legacy paper ID in identity index.")
                legacy_ids.add(legacy_id)
            for relative_path in record.relative_paths:
                if relative_path in relative_paths:
                    raise ValueError("Duplicate relative path in identity index.")
                relative_paths.add(relative_path)

    def _save_records(self, records: list[PaperIdentityRecord]) -> None:
        self._validate_unique(records)
        atomic_write_json(
            self.index_path,
            [record.model_dump(mode="json") for record in records],
        )
