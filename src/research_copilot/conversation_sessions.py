from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from research_copilot.storage import (
    atomic_write_json,
    read_json,
    validated_json_path,
)

DEFAULT_SESSION_ID = "default"
DEFAULT_SESSION_TITLE = "默认阅读"


class ConversationSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    title: str = Field(min_length=1, max_length=80)
    created_at: str


class ConversationSessionStore:
    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory.resolve()
        self._lock = RLock()

    def list_sessions(self, paper_id: str) -> list[ConversationSession]:
        with self._lock:
            path = self._session_path(paper_id)
            raw_sessions = read_json(path, None)
            if raw_sessions is None:
                default_session = self._default_session(paper_id)
                self._write_sessions(paper_id, [default_session])
                return [default_session]

            sessions = [
                ConversationSession.model_validate(session)
                for session in raw_sessions
            ]
            if not any(session.id == DEFAULT_SESSION_ID for session in sessions):
                sessions.insert(0, self._default_session(paper_id))
                self._write_sessions(paper_id, sessions)
            return sessions

    def create_session(self, paper_id: str, title: str) -> ConversationSession:
        with self._lock:
            cleaned_title = " ".join(title.strip().split())
            if not cleaned_title:
                raise ValueError("会话名称不能为空。")

            sessions = self.list_sessions(paper_id)
            if any(
                session.title.casefold() == cleaned_title.casefold()
                for session in sessions
            ):
                raise ValueError("当前论文已经有同名会话。")

            session = ConversationSession(
                id=uuid4().hex,
                paper_id=paper_id,
                title=cleaned_title,
                created_at=datetime.now(UTC).isoformat(),
            )
            sessions.append(session)
            self._write_sessions(paper_id, sessions)
            return session

    def contains(self, paper_id: str, session_id: str) -> bool:
        with self._lock:
            return any(
                session.id == session_id
                for session in self.list_sessions(paper_id)
            )

    @staticmethod
    def _default_session(paper_id: str) -> ConversationSession:
        return ConversationSession(
            id=DEFAULT_SESSION_ID,
            paper_id=paper_id,
            title=DEFAULT_SESSION_TITLE,
            created_at=datetime.now(UTC).isoformat(),
        )

    def _session_path(self, paper_id: str) -> Path:
        return validated_json_path(self.root_directory, paper_id)

    def _write_sessions(
        self,
        paper_id: str,
        sessions: list[ConversationSession],
    ) -> None:
        atomic_write_json(
            self._session_path(paper_id),
            [session.model_dump(mode="json") for session in sessions],
        )
