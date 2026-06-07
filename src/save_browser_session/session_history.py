"""
Session history module for tracking and suggesting recently used session names.

This module maintains a persistent history of session names to provide
quick-select suggestions for recurring workflows.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .session_analyzer import SessionNameSuggestion


@dataclass
class HistoricalSession:
    """
    Represents a previously used session name with usage metadata.

    Attributes:
        name: The session name
        timestamp: ISO format timestamp of first use
        use_count: Number of times this name has been used
        last_used: ISO format timestamp of most recent use
    """

    name: str
    timestamp: str
    use_count: int = 1
    last_used: Optional[str] = None


class SessionHistory:
    """Manages historical session names with persistence."""

    def __init__(self, history_file: Optional[Path] = None):
        """
        Initialize session history.

        Parameters:
            history_file: Path to history JSON file. If None, uses default location.
        """
        if history_file is None:
            # Store in application data directory
            app_dir = Path.home() / ".config" / "save_browser_session"
            app_dir.mkdir(parents=True, exist_ok=True)
            history_file = app_dir / "session_history.json"

        self.history_file = history_file
        self.sessions: List[HistoricalSession] = []
        self._load()

    def _load(self):
        """Load history from JSON file."""
        if not self.history_file.exists():
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.sessions = [
                    HistoricalSession(**item) for item in data.get("sessions", [])
                ]
        except (json.JSONDecodeError, TypeError, KeyError):
            # If file is corrupted, start fresh
            self.sessions = []

    def _save(self):
        """Save history to JSON file."""
        try:
            data = {
                "sessions": [asdict(s) for s in self.sessions],
                "version": "1.0",
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            # Silently fail - history is non-critical
            pass

    def add_session(self, name: str):
        """
        Add or update a session name in history.

        Skips empty names and "Autosaved" sessions.

        Parameters:
            name: The session name to record
        """
        # Skip empty names and autosaved sessions
        if not name or name == "Autosaved":
            return

        now = datetime.now().isoformat()

        # Check if name already exists
        existing = next((s for s in self.sessions if s.name == name), None)

        if existing:
            # Update existing entry
            existing.use_count += 1
            existing.last_used = now
        else:
            # Add new entry
            self.sessions.append(
                HistoricalSession(name=name, timestamp=now, use_count=1, last_used=now)
            )

        # Keep only last 50 unique names
        # Sort by last_used descending
        self.sessions.sort(key=lambda s: s.last_used or s.timestamp, reverse=True)
        self.sessions = self.sessions[:50]

        self._save()

    def get_recent_names(self, limit: int = 10) -> List[str]:
        """
        Get list of recently used session names.

        Parameters:
            limit: Maximum number of names to return

        Returns:
            List of session names, most recent first
        """
        # Already sorted by last_used in add_session
        return [s.name for s in self.sessions[:limit]]

    def get_suggestions(self, limit: int = 5) -> List[SessionNameSuggestion]:
        """
        Get historical names as suggestions with confidence scoring.

        More recent and frequently used names get higher confidence.

        Parameters:
            limit: Maximum number of suggestions

        Returns:
            List of SessionNameSuggestion objects
        """
        from .session_analyzer import SessionNameSuggestion

        suggestions: list[SessionNameSuggestion] = []

        for idx, session in enumerate(self.sessions[:limit]):
            # Base confidence on recency and frequency
            # Most recent = highest confidence (0.95)
            # Decays with position
            recency_score = 0.95 - (idx * 0.10)
            recency_score = max(recency_score, 0.50)

            # Boost confidence if used multiple times
            frequency_boost = min(session.use_count * 0.05, 0.15)
            confidence = min(recency_score + frequency_boost, 0.98)

            # Format last used time
            try:
                last_dt = datetime.fromisoformat(session.last_used or session.timestamp)
                time_ago = self._format_time_ago(last_dt)
                reasoning = f"Used {session.use_count}x, last {time_ago}"
            except Exception:
                reasoning = f"Used {session.use_count}x"

            suggestions.append(
                SessionNameSuggestion(
                    name=session.name,
                    confidence=confidence,
                    reasoning=reasoning,
                    category="history",
                )
            )

        return suggestions

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as relative time string."""
        now = datetime.now()
        delta = now - dt

        if delta.days > 30:
            return f"{delta.days // 30} month(s) ago"
        elif delta.days > 0:
            return f"{delta.days} day(s) ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} hour(s) ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} minute(s) ago"
        else:
            return "just now"
