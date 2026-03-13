"""state.py — Investigation session state management."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationState:
    """Tracks everything the player has discovered in one investigation session."""

    session_id: str
    case_id: str

    # What the player has unlocked
    discovered_entities: set[str] = field(default_factory=set)
    evidence_collected: set[str] = field(default_factory=set)
    interrogated_characters: set[str] = field(default_factory=set)
    contradictions_found: set[str] = field(default_factory=set)

    # Derived gates that have been satisfied (e.g. "investigate-servants")
    satisfied_gates: set[str] = field(default_factory=set)

    # Running chat memory (last N messages kept for AI context)
    chat_history: list[dict[str, str]] = field(default_factory=list)

    # Current stage
    stage: int = 1

    # Cap chat history at 20 messages to avoid token overflow
    MAX_HISTORY: int = 20

    def add_chat(self, role: str, content: str) -> None:
        self.chat_history.append({"role": role, "content": content})
        if len(self.chat_history) > self.MAX_HISTORY:
            self.chat_history = self.chat_history[-self.MAX_HISTORY:]


# ── Session store (in-memory, lost on restart) ───────────────────────────────

_SESSIONS: dict[str, InvestigationState] = {}


def create_session(case_id: str) -> InvestigationState:
    """Create a new investigation session and return it."""
    sid = uuid.uuid4().hex[:12]
    state = InvestigationState(session_id=sid, case_id=case_id)
    _SESSIONS[sid] = state
    return state


def get_session(session_id: str) -> InvestigationState | None:
    """Retrieve session by id, or None if expired/missing."""
    return _SESSIONS.get(session_id)


def list_sessions() -> dict[str, InvestigationState]:
    """Return all active sessions (debug)."""
    return _SESSIONS


# ── Graph cache — case-level, shared across all sessions ─────────────────────

_case_graph_cache: dict[str, dict] = {}
_graph_build_in_progress: dict[str, bool] = {}


def get_cached_graph(case_id: str) -> dict | None:
    """Return the cached merged graph for a case, or None if not yet built."""
    return _case_graph_cache.get(case_id)


def set_cached_graph(case_id: str, graph: dict) -> None:
    """Store the merged graph for a case in the in-memory cache."""
    _case_graph_cache[case_id] = graph


def is_graph_building(case_id: str) -> bool:
    """Return True if an AI graph build is currently in progress for this case."""
    return _graph_build_in_progress.get(case_id, False)


def set_graph_building(case_id: str, val: bool) -> None:
    """Set the in-progress flag for the AI graph build for a case."""
    _graph_build_in_progress[case_id] = val
