"""state.py — Investigation session state management."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, List, Set, Dict
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import SessionRecord
from app.database import AsyncSessionLocal

# ── Stage constants (shared with engine.py) ───────────────────────────────────

STAGE_NAMES: dict[int, str] = {
    1: "Crime Scene",
    2: "Forensic Analysis",
    3: "Witness Interviews",
    4: "Suspect Profiling",
    5: "Building the Case",
    6: "The Verdict",
}

STAGE_DESCRIPTIONS: dict[int, str] = {
    1: "The scene is fresh. Secure the perimeter, collect initial evidence, and identify the victims. What story does the bloodstain pattern tell?",
    2: "The lab results are coming in. Analyze fingerprints, DNA, and ballistics. Science doesn't lie, but it can be hard to read.",
    3: "People lie, forget, or see what they want to see. Interview the witnesses and look for the gaps in their stories.",
    4: "Every killer leaves a psychological footprint. Profile the suspects. Who had the motive, the means, and the cold heart to do this?",
    5: "The final pieces are falling into place. Confront the suspects with the truth. Watch for the moment they break.",
    6: "The file is complete. Review your evidence, name the perpetrator, and deliver justice. The truth is in your hands.",
}

STAGE_GATE_MAP: dict[int, str] = {
    1: "start",
    2: "gate-forensics",
    3: "gate-witnesses",
    4: "gate-suspects",
    5: "gate-case",
    6: "gate-verdict",
}


@dataclass
class TimelineEvent:
    """A significant event in the investigation timeline."""
    id: str
    timestamp: str  # ISO format
    type: str       # "discovery", "contradiction", "stage_advance", "note"
    title: str
    description: str
    stage: int
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return vars(self)

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

    # Derived gates that have been satisfied (e.g. "gate-forensics")
    satisfied_gates: set[str] = field(default_factory=set)

    # Running chat memory (last N messages kept for AI context)
    chat_history: list[dict[str, Any]] = field(default_factory=list)

    # ── Timeline ──────────────────────────────────────────────────────────────
    timeline: list[TimelineEvent] = field(default_factory=list)

    # ── Stage tracking ────────────────────────────────────────────────────────
    current_stage: int = 1
    completed_stages: list[int] = field(default_factory=list)
    message_count: int = 0

    # Frontend persistence data
    notes: str = ""
    graph_state: dict = field(default_factory=dict)

    @property
    def stage(self) -> int:
        return self.current_stage

    MAX_HISTORY: int = 20

    def add_chat(self, role: str, content: str, persona_id: str | None = None, persona_role: str = "co_detective") -> None:
        self.chat_history.append({
            "role": role,
            "content": content,
            "persona_id": persona_id,
            "persona_role": persona_role
        })
        if len(self.chat_history) > 200:
            self.chat_history = self.chat_history[-200:]
            
        if role == "user":
            self.message_count += 1

    def get_persona_history(self, persona_role: str, persona_id: str | None = None, limit: int = 10) -> list[dict[str, str]]:
        filtered = [
            {"role": m["role"], "content": m["content"]}
            for m in self.chat_history
            if m["persona_role"] == persona_role and m["persona_id"] == persona_id
        ]
        return filtered[-limit:]

    def add_timeline_event(self, event_type: str, title: str, description: str, meta: dict[str, Any] | None = None) -> None:
        event = TimelineEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=datetime.now().isoformat(),
            type=event_type,
            title=title,
            description=description,
            stage=self.current_stage,
            meta=meta or {}
        )
        self.timeline.append(event)

    @classmethod
    def from_record(cls, record: SessionRecord) -> InvestigationState:
        return cls(
            session_id=record.session_id,
            case_id=record.case_id,
            discovered_entities=set(record.discovered_entities or []),
            evidence_collected=set(record.evidence_collected or []),
            interrogated_characters=set(record.interrogated_characters or []),
            contradictions_found=set(record.contradictions_found or []),
            satisfied_gates=set(record.satisfied_gates or []),
            chat_history=record.chat_history or [],
            timeline=[TimelineEvent(**e) for e in (record.timeline or [])],
            current_stage=record.current_stage or 1,
            completed_stages=record.completed_stages or [],
            message_count=record.message_count or 0,
            notes=record.notes or "",
            graph_state=record.graph_state or {}
        )

    def to_record_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "case_id": self.case_id,
            "discovered_entities": list(self.discovered_entities),
            "evidence_collected": list(self.evidence_collected),
            "interrogated_characters": list(self.interrogated_characters),
            "contradictions_found": list(self.contradictions_found),
            "satisfied_gates": list(self.satisfied_gates),
            "chat_history": self.chat_history,
            "timeline": [e.to_dict() for e in self.timeline],
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "message_count": self.message_count,
            "notes": self.notes,
            "graph_state": self.graph_state
        }


# ── Database-backed Session Store ───────────────────────────────────────────

async def create_session(case_id: str) -> InvestigationState:
    """Create a new investigation session and persist it to the DB."""
    sid = uuid.uuid4().hex[:12]
    state = InvestigationState(session_id=sid, case_id=case_id)
    
    state.add_timeline_event(
        event_type="stage_advance",
        title="Investigation Started",
        description="The case file has been opened. Time to get to work.",
        meta={"stage_num": 1}
    )
    
    async with AsyncSessionLocal() as db:
        record = SessionRecord(**state.to_record_dict())
        db.add(record)
        await db.commit()
        
    return state


async def get_session(session_id: str) -> InvestigationState | None:
    """Retrieve session from DB by id, or None if missing."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SessionRecord).where(SessionRecord.session_id == session_id))
        record = result.scalar_one_or_none()
        if record:
            return InvestigationState.from_record(record)
    return None


async def save_session(state: InvestigationState) -> None:
    """Save the current state back to the database."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(SessionRecord)
            .where(SessionRecord.session_id == state.session_id)
            .values(**state.to_record_dict())
        )
        await db.commit()


# ── Graph cache — case-level, remains in-memory for now ─────────────────────
# (Graph building is expensive and static per case, so in-memory is fine)

_case_graph_cache: dict[str, dict] = {}
_graph_build_in_progress: dict[str, bool] = {}

def get_cached_graph(case_id: str) -> dict | None:
    return _case_graph_cache.get(case_id)

def set_cached_graph(case_id: str, graph: dict) -> None:
    _case_graph_cache[case_id] = graph

def is_graph_building(case_id: str) -> bool:
    return _graph_build_in_progress.get(case_id, False)

def set_graph_building(case_id: str, val: bool) -> None:
    _graph_build_in_progress[case_id] = val
