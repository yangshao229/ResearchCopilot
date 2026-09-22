from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from research_copilot.conversation_sessions import ConversationSessionStore


def test_session_store_creates_default_and_named_sessions(tmp_path: Path) -> None:
    store = ConversationSessionStore(tmp_path)

    default_session = store.list_sessions("paper-a")[0]
    method_session = store.create_session("paper-a", "  理解方法  ")

    assert default_session.id == "default"
    assert method_session.title == "理解方法"
    assert [session.title for session in store.list_sessions("paper-a")] == [
        "默认阅读",
        "理解方法",
    ]
    assert store.contains("paper-a", method_session.id)


def test_session_store_isolates_papers_and_rejects_duplicate_titles(
    tmp_path: Path,
) -> None:
    store = ConversationSessionStore(tmp_path)
    first = store.create_session("paper-a", "检查实验")

    assert store.contains("paper-b", first.id) is False
    with pytest.raises(ValueError, match="同名会话"):
        store.create_session("paper-a", "检查实验")


def test_concurrent_first_reads_create_one_valid_default_session(
    tmp_path: Path,
) -> None:
    store = ConversationSessionStore(tmp_path)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda _: store.list_sessions("paper-id"),
                range(8),
            )
        )

    assert all(
        [session.id for session in result] == ["default"]
        for result in results
    )
    assert [session.id for session in store.list_sessions("paper-id")] == [
        "default"
    ]
