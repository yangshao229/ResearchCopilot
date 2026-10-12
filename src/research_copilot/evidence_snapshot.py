"""Bounded, process-local handoff of evidence already shown to a reader."""

from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe
from threading import Lock
from time import monotonic
from typing import Callable

from research_copilot.domain import (
    EvidenceSet,
    ScopePreference,
    SearchMode,
    SourceDocumentRef,
)


class EvidenceSnapshotUnavailable(ValueError):
    """The preview cannot safely be reused; the reader must search again."""


@dataclass(frozen=True)
class EvidenceSnapshotKey:
    paper_id: str
    source_document: SourceDocumentRef
    query: str
    mode: SearchMode
    limit: int
    scope_preference: ScopePreference


class EvidenceSnapshotStore:
    def __init__(
        self,
        max_entries: int = 128,
        ttl_seconds: float = 15 * 60,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_entries < 1 or ttl_seconds <= 0:
            raise ValueError("Snapshot limits must be positive.")
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, tuple[float, EvidenceSnapshotKey, EvidenceSet]] = {}
        self._lock = Lock()

    def issue(self, key: EvidenceSnapshotKey, evidence_set: EvidenceSet) -> str:
        if evidence_set.origin != "retrieval" or evidence_set.query != key.query:
            raise ValueError("Only matching retrieved evidence can be previewed.")
        if any(
            candidate.source is None
            or candidate.source != key.source_document.at_page(candidate.source_page)
            for candidate in evidence_set.candidates
        ):
            raise ValueError("Snapshot candidates need current PDF anchors.")
        token = token_urlsafe(32)
        with self._lock:
            now = self._clock()
            self._remove_expired(now)
            while len(self._entries) >= self._max_entries:
                oldest = next(iter(self._entries))
                del self._entries[oldest]
            self._entries[token] = (
                now + self._ttl_seconds,
                key,
                evidence_set.model_copy(deep=True),
            )
        return token

    def resolve(self, token: str, key: EvidenceSnapshotKey) -> EvidenceSet:
        with self._lock:
            self._remove_expired(self._clock())
            entry = self._entries.get(token)
            if entry is None or entry[1] != key:
                raise EvidenceSnapshotUnavailable(
                    "刚才查看的证据已过期，或论文／问题／检索设置已变化。请重新检索原文后再生成回答。"
                )
            return entry[2].model_copy(deep=True)

    def _remove_expired(self, now: float) -> None:
        for token, (deadline, _, _) in list(self._entries.items()):
            if deadline <= now:
                del self._entries[token]
