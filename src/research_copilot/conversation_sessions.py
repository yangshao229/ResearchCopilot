from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

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
            if not path.exists():
                default_session = self._default_session(paper_id)
                self._write_sessions(paper_id, [default_session])
                return [default_session]

            with path.open("r", encoding="utf-8") as session_file:
                raw_sessions = json.load(session_file)
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
        if not re.fullmatch(r"[A-Za-z0-9_-]+", paper_id):
            raise ValueError("Invalid paper id.")
        return self.root_directory / f"{paper_id}.json"

    def _write_sessions(
        self,
        paper_id: str,
        sessions: list[ConversationSession],
    ) -> None:
        self.root_directory.mkdir(parents=True, exist_ok=True)
        path = self._session_path(paper_id)
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary_path.write_text(
            json.dumps(
                [session.model_dump(mode="json") for session in sessions],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
