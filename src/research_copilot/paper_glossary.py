from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from threading import RLock
from uuid import uuid4

from research_copilot.domain import GlossaryEntry, TranslationLanguage
from research_copilot.storage import atomic_write_json, read_json, validated_json_path

MAX_MATCHED_TERMS = 8


class PaperGlossaryStore:
    """User-confirmed terminology, stored locally for one paper at a time."""

    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory.resolve()
        self._lock = RLock()

    def list_entries(self, paper_id: str) -> list[GlossaryEntry]:
        with self._lock:
            return [
                GlossaryEntry.model_validate(item)
                for item in read_json(self._path(paper_id), [])
            ]

    def add_entry(
        self,
        paper_id: str,
        source: str,
        translation: str,
        target_language: TranslationLanguage,
    ) -> GlossaryEntry:
        cleaned_source = " ".join(source.split())
        cleaned_translation = " ".join(translation.split())
        if not cleaned_source or not cleaned_translation:
            raise ValueError("术语原文和指定译名不能为空。")
        with self._lock:
            entries = self.list_entries(paper_id)
            if any(
                item.source.casefold() == cleaned_source.casefold()
                and item.target_language == target_language
                for item in entries
            ):
                raise ValueError("当前论文的该目标语言中已有此术语，请先删除旧条目。")
            entry = GlossaryEntry(
                id=uuid4().hex,
                source=cleaned_source,
                translation=cleaned_translation,
                target_language=target_language,
            )
            entries.append(entry)
            self._write(paper_id, entries)
            return entry

    def delete_entry(self, paper_id: str, entry_id: str) -> None:
        with self._lock:
            entries = self.list_entries(paper_id)
            remaining = [entry for entry in entries if entry.id != entry_id]
            if len(remaining) == len(entries):
                raise KeyError(entry_id)
            self._write(paper_id, remaining)

    def _path(self, paper_id: str) -> Path:
        return validated_json_path(self.root_directory, paper_id)

    def _write(self, paper_id: str, entries: list[GlossaryEntry]) -> None:
        atomic_write_json(
            self._path(paper_id),
            [entry.model_dump(mode="json") for entry in entries],
        )


def match_glossary_entries(
    entries: list[GlossaryEntry],
    selected_text: str,
    context_text: str,
    target_language: TranslationLanguage,
) -> list[GlossaryEntry]:
    def matches(source: str, text: str) -> bool:
        pattern = re.escape(source).replace(r"\ ", r"\s+")
        if source[0].isascii() and (source[0].isalnum() or source[0] == "_"):
            pattern = r"(?<!\w)" + pattern
        if source[-1].isascii() and (source[-1].isalnum() or source[-1] == "_"):
            pattern += r"(?!\w)"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    ranked = []
    for entry in entries:
        if entry.target_language != target_language:
            continue
        in_selection = matches(entry.source, selected_text)
        if in_selection or matches(entry.source, context_text):
            ranked.append((not in_selection, -len(entry.source), entry.source.casefold(), entry))
    ranked.sort(key=lambda item: item[:3])
    return [item[3] for item in ranked[:MAX_MATCHED_TERMS]]


def glossary_signature(entries: list[GlossaryEntry]) -> str:
    values = sorted(
        (entry.source.casefold(), entry.translation, entry.target_language)
        for entry in entries
    )
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
