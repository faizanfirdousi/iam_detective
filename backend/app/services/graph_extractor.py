"""graph_extractor.py — AI-powered graph extraction from DO AI Agents.

Makes 4 parallel domain passes (people, evidence, locations, timeline) plus a
synthesis pass against each case's dedicated DO AI Agent endpoint.
Returns structured {nodes, edges} for merging with the static schema.
"""
from __future__ import annotations

import asyncio
import json
import os

import json_repair
from openai import AsyncOpenAI

# Mirrors the same env-var pattern used by do_agent.py (_ACCESS_KEY suffix).
AGENT_CONFIG: dict[str, dict[str, str | None]] = {
    "zodiac-killer": {
        "endpoint": os.getenv("DO_AGENT_ZODIAC_ENDPOINT"),
        "key": os.getenv("DO_AGENT_ZODIAC_ACCESS_KEY"),
    },
    "aarushi-talwar": {
        "endpoint": os.getenv("DO_AGENT_AARUSHI_ENDPOINT"),
        "key": os.getenv("DO_AGENT_AARUSHI_ACCESS_KEY"),
    },
    "oj-simpson": {
        "endpoint": os.getenv("DO_AGENT_OJ_ENDPOINT"),
        "key": os.getenv("DO_AGENT_OJ_ACCESS_KEY"),
    },
}

# Four focused domain passes — run in parallel
EXTRACTION_PROMPTS: dict[str, str] = {
    "people": (
        "[EXTRACT_GRAPH] You are a forensic analyst extracting structured data from "
        "the case knowledge base. Extract every named person in this case: suspects, "
        "victims, witnesses, detectives, lawyers, family members. "
        "For each person return a node with: id (slug), label (full name), "
        "type=PERSON, description (2-3 sentences), confidence (0-1), "
        "importance (HIGH/MEDIUM/LOW), unlock_level (1-5, 1=always visible). "
        "For edges between people include: source, target, relationship "
        "(e.g. KNEW, ALIBI_FOR, TESTIFIED_AGAINST, MOTIVE_AGAINST, FAMILY_OF), "
        "description, confidence, unlock_level. "
        "Return ONLY valid JSON: {\"nodes\": [...], \"edges\": [...]}"
    ),
    "evidence": (
        "[EXTRACT_GRAPH] You are a forensic analyst extracting structured data from "
        "the case knowledge base. Extract every piece of physical and forensic evidence "
        "in this case. "
        "For each item return a node with: id (slug), label, type=EVIDENCE, "
        "description (2-3 sentences), confidence (0-1), importance (HIGH/MEDIUM/LOW), "
        "unlock_level (1-5). "
        "For edges: which suspect this implicates (IMPLICATES), which detective "
        "found it (FOUND_BY), which location it came from (FOUND_AT), "
        "which alibi it contradicts (CONTRADICTS). "
        "Return ONLY valid JSON: {\"nodes\": [...], \"edges\": [...]}"
    ),
    "locations": (
        "[EXTRACT_GRAPH] You are a forensic analyst extracting structured data from "
        "the case knowledge base. Extract every key location: crime scenes, residences, "
        "places suspects were seen before or after the crime. "
        "For each location return a node with: id (slug), label, type=LOCATION, "
        "description (2-3 sentences), confidence (0-1), importance (HIGH/MEDIUM/LOW), "
        "unlock_level (1-5). "
        "For edges: which events happened here (SCENE_OF), which persons were "
        "present (PRESENT_AT), what evidence was found (CONTAINS_EVIDENCE). "
        "Return ONLY valid JSON: {\"nodes\": [...], \"edges\": [...]}"
    ),
    "timeline": (
        "[EXTRACT_GRAPH] You are a forensic analyst extracting structured data from "
        "the case knowledge base. Extract the key chronological events as TIMELINE nodes. "
        "For each event return a node with: id (slug), label (short event name), "
        "type=TIMELINE, description (date/time + what happened), confidence (0-1), "
        "importance (HIGH/MEDIUM/LOW), unlock_level (1-5). "
        "For edges: who was present (PRESENT_AT), what evidence was created "
        "(CREATED_EVIDENCE), how it supports or contradicts an alibi (SUPPORTS/CONTRADICTS). "
        "Return ONLY valid JSON: {\"nodes\": [...], \"edges\": [...]}"
    ),
}


def _clean_json_response(raw: str) -> dict:
    """Strip markdown fences and parse/repair JSON from agent output."""
    raw = raw.strip()
    # Strip ```json ... ``` fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # Try stdlib first (fastest), fall back to json_repair
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = json.loads(json_repair.repair_json(raw))

    if not isinstance(result, dict):
        return {"nodes": [], "edges": []}
    return result


async def _single_extraction(case_id: str, prompt_key: str) -> dict:
    """Run one domain extraction pass against the case's DO AI Agent."""
    cfg = AGENT_CONFIG[case_id]
    endpoint = (cfg.get("endpoint") or "").rstrip("/")
    key = cfg.get("key") or ""

    if not endpoint or not key:
        raise RuntimeError(
            f"Missing DO agent config for {case_id} "
            f"(check DO_AGENT_{case_id.upper().replace('-','_')}_ENDPOINT/ACCESS_KEY)"
        )

    client = AsyncOpenAI(
        base_url=f"{endpoint}/api/v1/",
        api_key=key,
    )
    response = await client.chat.completions.create(
        model="n/a",
        messages=[{"role": "user", "content": EXTRACTION_PROMPTS[prompt_key]}],
        extra_body={"include_retrieval_info": True},
        max_tokens=4096,
    )
    raw = response.choices[0].message.content or ""
    return _clean_json_response(raw)


async def _synthesis_pass(case_id: str, merged_nodes: dict[str, dict]) -> dict:
    """
    Give the agent the already-found entities.
    Ask it to reason deeper — find hidden connections, unlock_level 4-5 stuff.
    """
    cfg = AGENT_CONFIG[case_id]
    endpoint = (cfg.get("endpoint") or "").rstrip("/")
    key = cfg.get("key") or ""

    if not endpoint or not key:
        raise RuntimeError(f"Missing DO agent config for synthesis pass: {case_id}")

    client = AsyncOpenAI(
        base_url=f"{endpoint}/api/v1/",
        api_key=key,
    )
    entity_summary = json.dumps(list(merged_nodes.values())[:30], indent=2)  # cap to avoid token overflow
    prompt = (
        f"[EXTRACT_GRAPH] You already know these entities:\n{entity_summary}\n\n"
        "Now act as a master detective. Find:\n"
        "1. Hidden connections not obvious from individual facts\n"
        "2. Contradictions between alibi claims and physical evidence\n"
        "3. Suspicious gaps — who is notably absent from a timeline\n"
        "4. Inferred relationships a skilled investigator would draw\n"
        "Return ONLY new nodes and edges not already listed above. "
        "All new items should have unlock_level 4 or 5 and confidence < 0.75. "
        "Return ONLY valid JSON: {\"nodes\": [...], \"edges\": [...]}"
    )
    response = await client.chat.completions.create(
        model="n/a",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
    )
    raw = response.choices[0].message.content or ""
    return _clean_json_response(raw)


async def build_full_case_graph(case_id: str) -> dict:
    """
    Build the full AI-enriched graph for a case.
    Runs 4 domain passes in parallel, then a synthesis pass.
    Returns {case_id, nodes: [...], edges: [...]}.
    """
    print(f"[graph_extractor] Starting extraction passes for {case_id}...")

    # Run all 4 domain passes in parallel
    results = await asyncio.gather(
        *[_single_extraction(case_id, k) for k in EXTRACTION_PROMPTS],
        return_exceptions=True,
    )

    merged_nodes: dict[str, dict] = {}
    merged_edges: list[dict] = []

    for i, result in enumerate(results):
        key = list(EXTRACTION_PROMPTS.keys())[i]
        if isinstance(result, Exception):
            print(f"[graph_extractor] Pass '{key}' failed: {result}")
            continue

        print(f"[graph_extractor] Pass '{key}': "
              f"{len(result.get('nodes', []))} nodes, "
              f"{len(result.get('edges', []))} edges")

        for node in result.get("nodes", []):
            nid = node.get("id")
            if not nid:
                continue
            # Keep highest-confidence version on id collision
            if nid not in merged_nodes or node.get("confidence", 0) > merged_nodes[nid].get("confidence", 0):
                merged_nodes[nid] = node

        merged_edges.extend(result.get("edges", []))

    # Synthesis pass — deeper detective reasoning
    try:
        print(f"[graph_extractor] Running synthesis pass for {case_id}...")
        synth = await _synthesis_pass(case_id, merged_nodes)
        for node in synth.get("nodes", []):
            nid = node.get("id")
            if nid:
                merged_nodes.setdefault(nid, node)
        merged_edges.extend(synth.get("edges", []))
        print(f"[graph_extractor] Synthesis added "
              f"{len(synth.get('nodes', []))} nodes, "
              f"{len(synth.get('edges', []))} edges")
    except Exception as e:
        print(f"[graph_extractor] Synthesis pass failed: {e}")

    # Deduplicate edges by (source, target, relationship)
    seen_edges: set[tuple] = set()
    unique_edges: list[dict] = []
    for e in merged_edges:
        key_tuple = (e.get("source"), e.get("target"), e.get("relationship"))
        if key_tuple not in seen_edges:
            seen_edges.add(key_tuple)
            unique_edges.append(e)

    total_nodes = len(merged_nodes)
    total_edges = len(unique_edges)
    print(f"[graph_extractor] Complete for {case_id}: "
          f"{total_nodes} nodes, {total_edges} edges")

    return {
        "case_id": case_id,
        "nodes": list(merged_nodes.values()),
        "edges": unique_edges,
    }
