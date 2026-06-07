from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List

import pytest

if TYPE_CHECKING:
    from save_browser_session.session_analyzer import SessionNameSuggestion

from save_browser_session.session_history import HistoricalSession, SessionHistory


@pytest.fixture
def temp_history_file(tmp_path: Path) -> Path:
    return tmp_path / "session_history.json"


@pytest.fixture
def history(temp_history_file: Path) -> SessionHistory:
    return SessionHistory(temp_history_file)


def test_init_creates_empty_history(
    history: SessionHistory, temp_history_file: Path
) -> None:
    assert history.sessions == []


def test_add_session_new(history: SessionHistory) -> None:
    history.add_session("Project Alpha")

    assert len(history.sessions) == 1
    session = history.sessions[0]
    assert session.name == "Project Alpha"
    assert session.use_count == 1
    assert isinstance(session.last_used, str)
    assert session.last_used  # Should not be empty


def test_add_session_existing_increments_count(history: SessionHistory) -> None:
    history.add_session("Project Alpha")
    first_timestamp = history.sessions[0].last_used

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    history.add_session("Project Alpha")

    assert len(history.sessions) == 1
    session = history.sessions[0]
    assert session.name == "Project Alpha"
    assert session.use_count == 2
    assert session.last_used > first_timestamp


def test_add_session_skips_ignored(history: SessionHistory) -> None:
    history.add_session("Autosaved")
    history.add_session("")
    # add_session expects str, but we test runtime handling of None/empty
    history.add_session(None)  # type: ignore[arg-type]

    assert len(history.sessions) == 0


def test_persistence(temp_history_file: Path) -> None:
    # Create one instance and save data
    h1 = SessionHistory(temp_history_file)
    h1.add_session("Persisted Session")

    # Create new instance pointing to same file
    h2 = SessionHistory(temp_history_file)

    assert len(h2.sessions) == 1
    assert h2.sessions[0].name == "Persisted Session"
    assert h2.sessions[0].use_count == 1


def test_get_suggestions(history: SessionHistory) -> None:
    # Add sessions with different timestamps/counts
    history.add_session("Recent Project")  # Count 1, resets timestamp

    # Mocking older session with higher count
    # We cheat by accessing internal list because add_session updates timestamp
    now = datetime.now()
    old_iso = now.isoformat()

    old_session = HistoricalSession(
        name="Frequent Old Project", timestamp=old_iso, last_used=old_iso, use_count=10
    )
    history.sessions.append(old_session)

    suggestions: List[SessionNameSuggestion] = history.get_suggestions()

    assert len(suggestions) == 2

    names = [s.name for s in suggestions]
    assert "Recent Project" in names
    assert "Frequent Old Project" in names

    # Verify categories
    assert suggestions[0].category == "history"


def test_history_limit(history: SessionHistory) -> None:
    # Add 60 unique sessions
    for i in range(60):
        # We need sleep or explicit timestamps to ensure sorting order
        # But add_session uses current time. Fast execution might have identical timestamps.
        # But list append order + stable sort might preserve order if timestamps identical?
        # Actually sessions are sorted by timestamp desc.
        history.add_session(f"Session {i}")

    assert len(history.sessions) <= 50

    # Since we added Session 0 first, Session 59 last,
    # Session 59 should be most recent.
    # Sessions 0-9 should be dropped.

    names = [s.name for s in history.sessions]
    assert "Session 59" in names
    assert "Session 0" not in names


def test_load_corrupted_file(temp_history_file: Path) -> None:
    with open(temp_history_file, "w") as f:
        f.write("{ invalid json }")

    h = SessionHistory(temp_history_file)
    assert h.sessions == []
