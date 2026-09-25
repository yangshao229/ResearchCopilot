from __future__ import annotations

from pathlib import Path
from threading import RLock

from research_copilot.domain import LanguagePolicy
from research_copilot.storage import atomic_write_json, read_json, validated_json_path


class PaperLanguagePreferenceStore:
    """Stores language defaults locally, isolated by paper id."""

    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory.resolve()
        self._lock = RLock()

    def get(self, paper_id: str) -> LanguagePolicy:
        with self._lock:
            raw = read_json(
                self._path(paper_id),
                LanguagePolicy().model_dump(mode="json"),
            )
            return LanguagePolicy.model_validate(raw)

    def save(self, paper_id: str, policy: LanguagePolicy) -> LanguagePolicy:
        with self._lock:
            atomic_write_json(
                self._path(paper_id),
                policy.model_dump(mode="json"),
            )
            return policy

    def _path(self, paper_id: str) -> Path:
        return validated_json_path(self.root_directory, paper_id)
