"""schema.py — Load and validate case schema JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_schemas"

# In-memory cache: case_id → parsed dict
_CACHE: dict[str, dict[str, Any]] = {}


def load_schema(case_id: str) -> dict[str, Any]:
    """Return the full parsed schema dict for a case, cached after first load."""
    if case_id in _CACHE:
        return _CACHE[case_id]

    path = _SCHEMA_DIR / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No schema for case '{case_id}' at {path}")

    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    _CACHE[case_id] = schema
    return schema


def get_entity(schema: dict[str, Any], entity_id: str) -> dict[str, Any] | None:
    """Find an entity by id in the schema."""
    for e in schema.get("entities", []):
        if e["id"] == entity_id:
            return e
    return None


def get_character(schema: dict[str, Any], character_id: str) -> dict[str, Any] | None:
    """Return character definition for a persona id (suspect/witness id)."""
    return schema.get("characters", {}).get(character_id)


def get_all_entity_ids(schema: dict[str, Any]) -> list[str]:
    """Return all entity ids defined in the schema."""
    return [e["id"] for e in schema.get("entities", [])]
