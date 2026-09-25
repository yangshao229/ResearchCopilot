from __future__ import annotations

from pathlib import Path
from threading import RLock

from research_copilot.paper_reading_guide import (
    PaperReadingGuide,
    build_reading_guide,
)
from research_copilot.paper_structure import PaperStructure, extract_paper_structure


class PaperDocumentService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._structure_cache: dict[
            tuple[str, int, int], PaperStructure
        ] = {}

    def structure(self, pdf_path: Path) -> PaperStructure:
        stat = pdf_path.stat()
        cache_key = (str(pdf_path.resolve()), stat.st_mtime_ns, stat.st_size)
        with self._lock:
            cached = self._structure_cache.get(cache_key)
            if cached is not None:
                return cached

        structure = extract_paper_structure(pdf_path)
        with self._lock:
            self._structure_cache = {
                key: value
                for key, value in self._structure_cache.items()
                if key[0] != cache_key[0]
            }
            self._structure_cache[cache_key] = structure
        return structure

    def reading_guide(self, pdf_path: Path) -> PaperReadingGuide:
        return build_reading_guide(self.structure(pdf_path))
