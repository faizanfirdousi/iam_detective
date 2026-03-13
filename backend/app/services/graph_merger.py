"""graph_merger.py — Merge static case schema with AI-extracted graph nodes/edges.

The schema is the source of truth for gate/reveal logic.
AI-extracted nodes either enrich empty fields on schema nodes, or add new nodes.
"""
from __future__ import annotations

from app.engine.schema import load_schema

# Map schema entity types → graph node types
ENTITY_TYPE_MAP: dict[str, str] = {
    "suspect": "PERSON",
    "victim": "PERSON",
    "witness": "PERSON",
    "detective": "PERSON",
    "lawyer": "PERSON",
    "evidence": "EVIDENCE",
    "location": "LOCATION",
    "event": "EVENT",
    "organization": "ORGANIZATION",
}


def _gate_to_unlock_level(revealed_at: object) -> int:
    """Convert the schema's gate system to a numeric unlock level (1-5)."""
    if revealed_at is None or revealed_at == "start":
        return 1
    if isinstance(revealed_at, dict):
        requires = revealed_at.get("requires", [])
        return min(5, 1 + len(requires))
    if isinstance(revealed_at, str):
        if revealed_at.startswith("gate-"):
            # gate-a → 2, gate-b → 3, gate-c → 4, etc.
            letter = revealed_at.replace("gate-", "")
            if letter and letter[0].isalpha():
                return min(5, 2 + (ord(letter[0].lower()) - ord("a")))
        # Numeric string: "1", "2", ...
        try:
            return min(5, max(1, int(revealed_at)))
        except ValueError:
            pass
    return 2


def merge_graph_with_schema(case_id: str, ai_graph: dict) -> dict:
    """
    Build the merged graph for a case.

    Parameters
    ----------
    case_id : str
        The case slug (e.g. "zodiac-killer").
    ai_graph : dict
        Result from build_full_case_graph (may be empty: {"nodes":[],"edges":[]}).

    Returns
    -------
    dict
        {case_id, nodes: [...], edges: [...]}
    """
    schema = load_schema(case_id)

    # ── Build authoritative nodes from the static schema ──────────────────
    static_nodes: dict[str, dict] = {}
    for entity in schema.get("entities", []):
        eid = entity.get("id")
        if not eid:
            continue
        revealed_at = entity.get("revealed_at", "start")
        static_nodes[eid] = {
            "id": eid,
            "label": entity.get("name") or entity.get("label") or eid,
            "type": ENTITY_TYPE_MAP.get(entity.get("type", "").lower(), "UNKNOWN"),
            "description": entity.get("description", ""),
            "image_url": entity.get("image_url"),
            "confidence": 1.0,
            "importance": entity.get("importance", "MEDIUM"),
            "revealed_at": revealed_at,
            "unlock_level": _gate_to_unlock_level(revealed_at),
            "unlock_keyword_triggers": entity.get("unlock_keyword_triggers", []),
            "source": "schema",
        }

    # ── Layer AI nodes on top ──────────────────────────────────────────────
    for ai_node in ai_graph.get("nodes", []):
        nid = ai_node.get("id")
        if not nid:
            continue
        if nid in static_nodes:
            # Only fill empty fields — never override schema data
            if not static_nodes[nid]["description"] and ai_node.get("description"):
                static_nodes[nid]["description"] = ai_node["description"]
            if not static_nodes[nid]["image_url"] and ai_node.get("image_url"):
                static_nodes[nid]["image_url"] = ai_node["image_url"]
        else:
            # Normalise unlock_level field if AI used a different name
            node = dict(ai_node)
            node.setdefault("unlock_level", 2)
            node.setdefault("confidence", 0.7)
            node.setdefault("importance", "MEDIUM")
            node.setdefault("source", "ai_extracted")
            static_nodes[nid] = node

    # ── Build edges from the static schema ────────────────────────────────
    schema_edges: list[dict] = []
    for conn in schema.get("connections", []):
        source = conn.get("from") or conn.get("source")
        target = conn.get("to") or conn.get("target")
        if not source or not target:
            continue
        schema_edges.append({
            "source": source,
            "target": target,
            "relationship": conn.get("type") or conn.get("relationship", "LINKED_TO"),
            "description": conn.get("description", ""),
            "confidence": 1.0,
            "unlock_level": _gate_to_unlock_level(conn.get("revealed_at")),
            "source_system": "schema",
        })

    ai_edges: list[dict] = [
        {**e, "source_system": "ai_extracted"}
        for e in ai_graph.get("edges", [])
    ]

    # Deduplicate — schema edges win on (source, target, relationship) collision
    seen: set[tuple] = set()
    all_edges: list[dict] = []
    for edge in schema_edges + ai_edges:
        key = (edge.get("source"), edge.get("target"), edge.get("relationship"))
        if key not in seen:
            seen.add(key)
            all_edges.append(edge)

    return {
        "case_id": case_id,
        "nodes": list(static_nodes.values()),
        "edges": all_edges,
    }
