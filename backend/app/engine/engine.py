"""engine.py — Investigation Engine: gates, triggers, contradictions, AI context, stage system."""

from __future__ import annotations

import logging
from typing import Any

from .schema import load_schema, get_character, get_entity
from .state import InvestigationState, STAGE_NAMES, STAGE_DESCRIPTIONS, STAGE_GATE_MAP

log = logging.getLogger(__name__)


# ── Gate resolution ───────────────────────────────────────────────────────────

def _gate_satisfied(revealed_at: Any, state: InvestigationState) -> bool:
    """
    Check whether an entity's visibility gate is satisfied.

    revealed_at can be:
      - "start"                              → always visible
      - {"requires": ["gate-a", "gate-b"]}   → all gates must be satisfied
    """
    if revealed_at == "start":
        return True

    if isinstance(revealed_at, dict):
        required = revealed_at.get("requires", [])
        return all(g in state.satisfied_gates for g in required)

    return False


# ── Visible entities ──────────────────────────────────────────────────────────

def get_visible_entities(state: InvestigationState) -> list[dict[str, Any]]:
    """Return only the entities whose gates are satisfied for this session."""
    schema = load_schema(state.case_id)
    visible = []
    for ent in schema.get("entities", []):
        if ent["id"] in state.discovered_entities or _gate_satisfied(ent.get("revealed_at", "start"), state):
            visible.append(ent)
            state.discovered_entities.add(ent["id"])
    return visible


def get_visible_connections(state: InvestigationState) -> list[dict[str, Any]]:
    """Return only connections whose gates are satisfied AND both endpoints are visible."""
    schema = load_schema(state.case_id)
    visible_ids = {e["id"] for e in get_visible_entities(state)}
    conns = []
    for conn in schema.get("connections", []):
        if conn["from"] in visible_ids and conn["to"] in visible_ids:
            if _gate_satisfied(conn.get("revealed_at", "start"), state):
                conns.append(conn)
    return conns


# ── Chat trigger processing ──────────────────────────────────────────────────

def process_chat_triggers(message: str, state: InvestigationState) -> list[dict[str, Any]]:
    """
    Scan a player message for keywords that unlock gated entities.
    Returns list of newly unlocked entities (for "evidence discovered!" toasts).
    """
    schema = load_schema(state.case_id)
    msg_lower = message.lower()
    newly_unlocked: list[dict[str, Any]] = []

    for ent in schema.get("entities", []):
        if ent["id"] in state.discovered_entities:
            continue  # already discovered

        triggers = ent.get("unlock_keyword_triggers", [])
        if not triggers:
            continue

        for keyword in triggers:
            if keyword.lower() in msg_lower:
                # Satisfy gate: the entity id itself acts as a gate for downstream entities
                state.discovered_entities.add(ent["id"])
                state.satisfied_gates.add(ent["id"])
                if ent["type"] == "evidence":
                    state.evidence_collected.add(ent["id"])

                # Also satisfy any gate names in the requires list
                revealed_at = ent.get("revealed_at", "start")
                if isinstance(revealed_at, dict):
                    for req in revealed_at.get("requires", []):
                        state.satisfied_gates.add(req)

                newly_unlocked.append(ent)
                
                # Add to timeline
                state.add_timeline_event(
                    event_type="discovery",
                    title=f"New {ent['type'].capitalize()}: {ent['name']}",
                    description=ent.get("description", ""),
                    meta={"entity_id": ent["id"], "trigger": keyword}
                )
                
                log.info("🔓 Unlocked: %s (trigger: '%s')", ent["name"], keyword)
                break  # don't double-trigger same entity

    return newly_unlocked


def satisfy_gate(gate_name: str, state: InvestigationState) -> list[dict[str, Any]]:
    """
    Manually satisfy a gate (e.g. player performs an action).
    Returns list of entities this newly reveals.
    """
    if gate_name in state.satisfied_gates:
        return []

    state.satisfied_gates.add(gate_name)

    # Check what new entities this reveals
    schema = load_schema(state.case_id)
    newly_visible = []
    for ent in schema.get("entities", []):
        if ent["id"] in state.discovered_entities:
            continue
        if _gate_satisfied(ent.get("revealed_at", "start"), state):
            state.discovered_entities.add(ent["id"])
            if ent["type"] == "evidence":
                state.evidence_collected.add(ent["id"])
            newly_visible.append(ent)
            # Entity id becomes a satisfiable gate for downstream
            state.satisfied_gates.add(ent["id"])

    return newly_visible


# ── Contradiction detection ───────────────────────────────────────────────────

def check_contradictions(state: InvestigationState) -> list[dict[str, Any]]:
    """
    Check if any character contradictions can be detected with current evidence.
    Returns list of contradiction dicts (id, claim, contradicted_by, confrontation_prompt).
    """
    schema = load_schema(state.case_id)
    found: list[dict[str, Any]] = []

    for char_id, char_data in schema.get("characters", {}).items():
        for contradiction in char_data.get("contradictions", []):
            c_id = contradiction["id"]
            if c_id in state.contradictions_found:
                continue  # already found

            contradicted_by = contradiction["contradicted_by"]
            if contradicted_by in state.evidence_collected or contradicted_by in state.discovered_entities:
                # Player has the evidence that contradicts this claim
                if char_id in state.interrogated_characters or char_id in state.discovered_entities:
                    state.contradictions_found.add(c_id)
                    found.append({
                        "character_id": char_id,
                        **contradiction,
                    })
                    
                    # Add to timeline
                    state.add_timeline_event(
                        event_type="contradiction",
                        title=f"Contradiction Detected: {char_id}",
                        description=f"Claim: '{contradiction['claim']}' is contradicted by evidence: '{contradicted_by}'",
                        meta={"character_id": char_id, "contradiction_id": c_id, "evidence_id": contradicted_by}
                    )
                    
                    log.info("⚡ Contradiction detected: %s", c_id)

    return found


# ── Stage system ─────────────────────────────────────────────────────────────

# Stage-advance minimum requirements
_STAGE_REQUIREMENTS: dict[int, dict[str, int]] = {
    1: {"min_entities_viewed": 2,  "min_chat_messages": 1,  "contradictions_found": 0},
    2: {"min_entities_viewed": 4,  "min_chat_messages": 3,  "contradictions_found": 0},
    3: {"min_entities_viewed": 6,  "min_chat_messages": 5,  "contradictions_found": 0},
    4: {"min_entities_viewed": 8,  "min_chat_messages": 7,  "contradictions_found": 0},
    5: {"min_entities_viewed": 10, "min_chat_messages": 10, "contradictions_found": 1},
    6: {},  # always openable once stage 5 is complete
}


def can_advance_stage(state: InvestigationState) -> dict[str, Any]:
    """
    Check if player has done enough in current stage to advance.
    Returns a dict with `can_advance` bool and per-requirement status.
    """
    stage = state.current_stage
    if stage >= 6:
        return {
            "can_advance": False,
            "reason": "Already at final stage",
            "requirements_met": {},
            "current_stage": stage,
        }

    req = _STAGE_REQUIREMENTS.get(stage, {})
    met: dict[str, bool] = {}

    if "min_entities_viewed" in req:
        met["min_entities_viewed"] = len(state.discovered_entities) >= req["min_entities_viewed"]
    if "min_chat_messages" in req:
        met["min_chat_messages"] = state.message_count >= req["min_chat_messages"]
    if "contradictions_found" in req and req["contradictions_found"] > 0:
        met["contradictions_found"] = len(state.contradictions_found) >= req["contradictions_found"]

    return {
        "can_advance": all(met.values()),
        "requirements_met": met,
        "current_stage": stage,
        "requirements": req,
    }


def advance_stage(state: InvestigationState) -> dict[str, Any]:
    """
    Advance the player to the next investigation stage.
    Unlocks the stage gate, returns newly visible entities.
    Called only after can_advance_stage() confirms readiness (enforced in route).
    """
    if state.current_stage >= 6:
        return {"advanced": False, "reason": "Already at final stage"}

    next_stage = state.current_stage + 1
    gate_to_unlock = STAGE_GATE_MAP[next_stage]

    # Mark current stage completed
    if state.current_stage not in state.completed_stages:
        state.completed_stages.append(state.current_stage)

    # Unlock all stage gates up to and including next_stage
    # (handles edge cases where a player skips via keyword triggers)
    for s in range(2, next_stage + 1):
        g = STAGE_GATE_MAP[s]
        if g not in state.satisfied_gates:
            state.satisfied_gates.add(g)

    # Move stage pointer
    state.current_stage = next_stage

    # Add to timeline
    state.add_timeline_event(
        event_type="stage_advance",
        title=f"Advanced to Stage {next_stage}: {STAGE_NAMES[next_stage]}",
        description=STAGE_DESCRIPTIONS[next_stage],
        meta={"stage_num": next_stage}
    )

    # Discover newly visible entities
    schema = load_schema(state.case_id)
    newly_visible = []
    for ent in schema.get("entities", []):
        if ent["id"] in state.discovered_entities:
            continue
        if _gate_satisfied(ent.get("revealed_at", "start"), state):
            state.discovered_entities.add(ent["id"])
            if ent["type"] == "evidence":
                state.evidence_collected.add(ent["id"])
            newly_visible.append(ent)
            state.satisfied_gates.add(ent["id"])

    log.info(
        "🚀 Stage advanced → %d (%s). Newly visible: %d entities.",
        next_stage, STAGE_NAMES[next_stage], len(newly_visible),
    )

    return {
        "advanced": True,
        "new_stage": next_stage,
        "stage_name": STAGE_NAMES[next_stage],
        "stage_description": STAGE_DESCRIPTIONS[next_stage],
        "newly_unlocked_entities": [
            {"id": e["id"], "name": e["name"], "type": e["type"]}
            for e in newly_visible
        ],
        "graph_event": "STAGE_ADVANCE",
    }


# ── AI context building ──────────────────────────────────────────────────────

def build_ai_context(
    state: InvestigationState,
    role: str,
    persona_id: str | None = None,
) -> str:
    """
    Build a system prompt that restricts the AI to ONLY information the player has discovered.
    This is the core of knowledge isolation.
    """
    schema = load_schema(state.case_id)
    visible = get_visible_entities(state)
    visible_names = [e["name"] for e in visible]

    # Base case context
    lines = [
        f"ACTIVE CASE: {schema.get('title', state.case_id)}",
        "",
        "INVESTIGATION RULES — FOLLOW STRICTLY:",
        "- You may ONLY reference entities and facts the detective has already discovered.",
        "- Do NOT reveal information about entities the detective has NOT yet uncovered.",
        f"- Currently discovered entities: {', '.join(visible_names)}",
        "- If asked about something not yet discovered, say 'We don't have that information yet.' or 'That hasn't come up in the investigation.'",
        "",
    ]

    # Role-specific context
    if role == "co_detective":
        lines.append("You are the Lead Detective's partner. You are sharp, observant, and slightly noir.")
        lines.append(f"Current Phase: {STAGE_NAMES.get(state.current_stage, 'Investigation')}")
        lines.append(f"Mission: {STAGE_DESCRIPTIONS.get(state.current_stage, '')}")
        lines.append("\nYOUR OBJECTIVES:")
        lines.append("- Actively suggest what to investigate next based on the current stage.")
        lines.append("- If we're at the Crime Scene, focus on physical details and initial impressions.")
        lines.append("- If we're in Forensics, help analyze the DNA or ballistics reports.")
        lines.append("- NEVER reveal future stage secrets. Only talk about what we've discovered.")
        lines.append("- Be conversational, like a partner in a squad car. Don't just list facts.")

    elif role in ("witness", "suspect") and persona_id:
        char = get_character(schema, persona_id)
        if char:
            lines.append(f"ROLE: You are {char['persona']}")
            lines.append(f"KNOWLEDGE BOUNDARY: {char['knowledge_boundary']}")
            lines.append("Stay in character. Only answer based on your knowledge boundary.")
            lines.append("If asked about facts outside your knowledge, say 'I don't know about that' or 'That's not something I was involved in.'")

            # Check if player has evidence for confrontation
            for contradiction in char.get("contradictions", []):
                if contradiction["contradicted_by"] in state.evidence_collected:
                    lines.append(f"\n⚠️ PRESSURE: The detective has evidence contradicting your claim: '{contradiction['claim']}'")
                    lines.append(f"If confronted, become defensive but slowly reveal more. {contradiction['confrontation_prompt']}")

            state.interrogated_characters.add(persona_id)
        else:
            lines.append(f"You are a {role} in this case. Stay in character.")
    else:
        lines.append(f"You are a {role} in this case.")

    # Append discovered evidence summary
    if state.evidence_collected:
        evidence_entities = [e for e in visible if e["id"] in state.evidence_collected]
        lines.append("\nEVIDENCE COLLECTED SO FAR:")
        for ev in evidence_entities:
            lines.append(f"  • {ev['name']}: {ev['description']}")

    # Append known contradictions
    if state.contradictions_found:
        lines.append("\nCONTRADICTIONS DETECTED:")
        for char_id, char_data in schema.get("characters", {}).items():
            for c in char_data.get("contradictions", []):
                if c["id"] in state.contradictions_found:
                    lines.append(f"  • {char_id}: Claimed '{c['claim']}' but evidence '{c['contradicted_by']}' contradicts this.")

    return "\n".join(lines)


# ── Final deduction scoring ──────────────────────────────────────────────────

def evaluate_conclusion(
    state: InvestigationState,
    submission: dict[str, Any],
) -> dict[str, Any]:
    """
    Score the player's final deduction against the case solution.
    submission: { killer: str, motive: str, method: str }
    Returns: { score: int, max_score: int, feedback: str, official_verdict: str }
    """
    schema = load_schema(state.case_id)
    solution = schema.get("solution", {})

    score = 0
    max_score = 0
    feedback_parts = []

    # 1. Suspect identification (40 points)
    max_score += 40
    submitted_killer = (submission.get("killer") or "").lower()
    primary = [s.lower() for s in solution.get("primary_suspects", [])]
    secondary = [s.lower() for s in solution.get("secondary_suspects", [])]

    if any(p in submitted_killer or submitted_killer in p for p in primary):
        score += 40
        feedback_parts.append("✅ Correct primary suspect identified.")
    elif any(s in submitted_killer or submitted_killer in s for s in secondary):
        score += 20
        feedback_parts.append("⚠️ You identified a secondary suspect — plausible but not the primary lead.")
    else:
        feedback_parts.append("❌ Suspect identification does not match known suspects.")

    # 2. Evidence coverage (30 points)
    max_score += 30
    total_evidence = sum(1 for e in schema.get("entities", []) if e["type"] == "evidence")
    collected = len(state.evidence_collected)
    evidence_pct = (collected / total_evidence * 100) if total_evidence > 0 else 0
    evidence_score = min(30, int(collected / total_evidence * 30)) if total_evidence > 0 else 0
    score += evidence_score
    feedback_parts.append(f"📋 Evidence collected: {collected}/{total_evidence} ({evidence_pct:.0f}%)")

    # 3. Contradictions found (20 points)
    max_score += 20
    total_contradictions = sum(
        len(c.get("contradictions", []))
        for c in schema.get("characters", {}).values()
    )
    found = len(state.contradictions_found)
    if total_contradictions > 0:
        contra_score = min(20, int(found / total_contradictions * 20))
        score += contra_score
        feedback_parts.append(f"⚡ Contradictions exposed: {found}/{total_contradictions}")
    else:
        score += 20  # no contradictions to find
        feedback_parts.append("⚡ No contradictions in this case schema.")

    # 4. Motive provided (10 points — just checking non-empty)
    max_score += 10
    if submission.get("motive", "").strip():
        score += 10
        feedback_parts.append("✅ Motive theory provided.")
    else:
        feedback_parts.append("❌ No motive provided.")

    # 5. Stage completion bonus
    stages_completed = len(state.completed_stages)
    stage_bonus = stages_completed * 2  # 2 pts per completed stage (max 10)
    feedback_parts.append(f"🔓 Investigation depth: {stages_completed}/5 stages fully explored (+{stage_bonus} bonus pts)")

    return {
        "score": score,
        "max_score": max_score,
        "percentage": round(score / max_score * 100) if max_score > 0 else 0,
        "feedback": "\n".join(feedback_parts),
        "official_verdict": solution.get("official_verdict", "Unknown"),
        "entities_discovered": len(state.discovered_entities),
        "total_entities": len(schema.get("entities", [])),
    }
