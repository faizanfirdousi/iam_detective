from __future__ import annotations

import glob
import json
import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from app.data.cases import list_cases, get_case_ids
from app.data.images import patch_node_images
from app.models import (
    CaseDetail, CaseListItem, CaseIntroSlide, ChatRequest, ChatResponse, LinkBoard,
    TimelineResponse, TimelineEventModel
)
from app.services.chat import gradient_chat
from app.services.do_agent import DOAgentClient

# Graph services
from app.services.graph_extractor import build_full_case_graph
from app.services.graph_merger import merge_graph_with_schema

# Engine imports
from app.engine.state import (
    create_session, get_session, save_session,
    get_cached_graph, set_cached_graph,
    is_graph_building, set_graph_building,
)
from app.database import engine, Base
from app.engine.schema import load_schema
from app.engine import engine as inv_engine
from app.engine.state import STAGE_NAMES, STAGE_DESCRIPTIONS
from app.services.do_agent import build_stage_prefix


load_dotenv()

app = FastAPI(title="IAM Detective API", version="0.4.0")

from fastapi import APIRouter
api_router = APIRouter()


cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_case(case_id: str) -> None:
    if case_id not in get_case_ids():
        raise HTTPException(status_code=404, detail=f"case_not_found:{case_id}")


def _get_client(case_id: str) -> DOAgentClient:
    try:
        return DOAgentClient(case_id=case_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


async def _require_session(session_id: str):
    state = await get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return state


# ── Startup: preload any pre-generated graph JSON files from disk ─────────────

@app.on_event("startup")
async def startup_event() -> None:
    # 1. Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[startup] Database tables verified.")

    # 2. Preload graphs
    schema_dir = os.path.join(os.path.dirname(__file__), "data", "case_schemas")
    for path in glob.glob(os.path.join(schema_dir, "*-graph.json")):
        case_id = os.path.basename(path).replace("-graph.json", "")
        try:
            with open(path) as f:
                set_cached_graph(case_id, json.load(f))
            print(f"[startup] Loaded pre-generated graph: {case_id}")
        except Exception as e:
            print(f"[startup] Failed to load graph {path}: {e}")


# ── Health & case listing ─────────────────────────────────────────────────────

@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/cases", response_model=list[CaseListItem])
def api_list_cases() -> list[CaseListItem]:
    return list_cases()


@api_router.get("/cases/{case_id}", response_model=CaseDetail)
async def api_get_case(case_id: str) -> CaseDetail:
    _require_case(case_id)
    client = _get_client(case_id)

    resp = await client.chat_completions(
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are generating the intro for the detective game case: {case_id}. "
                    "Use ONLY the attached knowledge base for this case. "
                    "Return ONLY valid JSON with keys: "
                    "title (string), status (solved|unsolved|pending), "
                    "opening_lines (array of 3-5 short evocative strings), "
                    "sources (array of source filenames/urls if available). "
                    "Do not include any extra keys. Do not invent facts."
                ),
            },
            {"role": "user", "content": f"case_id={case_id}\nGenerate the case intro JSON."},
        ],
        include_retrieval_info=True,
    )

    content = client.extract_content(resp)
    try:
        obj = client.extract_json_object(content)
        detail = CaseDetail.model_validate({"id": case_id, **obj})
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"agent_invalid_json:{e}")

    return detail


@api_router.get("/cases/{case_id}/intro", response_model=list[CaseIntroSlide])
async def api_get_intro_slides(case_id: str) -> list[CaseIntroSlide]:
    _require_case(case_id)
    client = _get_client(case_id)

    resp = await client.chat_completions(
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are generating cinematic story intro slides for a detective game about case: {case_id}. "
                    "Use ONLY facts from the attached knowledge base. "
                    "Return ONLY a valid JSON object with a single key 'slides' containing an array of exactly 4 objects. "
                    "Each object has keys: \"page\" (int 1-4), "
                    "\"text\" (string, 2-4 noir sentences), "
                    "\"image_prompt\" (string, short dark description). "
                    "Slide 1: Time/place/discovery. Slide 2: Crime facts. "
                    "Slide 3: The mystery. Slide 4: Investigation begins. "
                    "Return ONLY the JSON object."
                ),
            },
            {"role": "user", "content": f"case_id={case_id}\nGenerate 4 cinematic intro slides as JSON."},
        ],
        include_retrieval_info=True,
    )

    content = client.extract_content(resp).strip()
    try:
        obj = client.extract_json_object(content)
        slides_raw = obj.get("slides") or obj.get("intro_slides") or obj.get("pages")
        if slides_raw is None:
            slides_raw = client.extract_json_array(content)
        if not isinstance(slides_raw, list):
            raise ValueError("slides_key_not_a_list")
        slides = [CaseIntroSlide.model_validate(s) for s in slides_raw]
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"agent_invalid_json:{e}")

    return slides


# ── Legacy linkboard + chat (no session, no investigation logic) ──────────────

@api_router.get("/cases/{case_id}/linkboard", response_model=LinkBoard)
async def api_get_linkboard(case_id: str, stage: int = 1) -> LinkBoard:
    _require_case(case_id)
    client = _get_client(case_id)

    stage = max(1, min(int(stage), 5))
    resp = await client.chat_completions(
        messages=[
            {
                "role": "system",
                "content": (
                    f"Generate a link-board graph for case: {case_id}. "
                    "Use ONLY the attached knowledge base. "
                    "Return ONLY JSON with keys: nodes, edges. "
                    "nodes: [{id, type (suspect|victim|witness|evidence|location|event), "
                    "name, description, image_url (Wikimedia URL or null), revealed_at_stage (1-5)}]. "
                    "edges: [{from, to, label, revealed_at_stage}]. "
                    f"Only include revealed_at_stage <= {stage}."
                ),
            },
            {"role": "user", "content": f"case_id={case_id}\nstage={stage}\nGenerate link-board JSON."},
        ],
        include_retrieval_info=True,
    )

    content = client.extract_content(resp)
    try:
        obj = client.extract_json_object(content)
        if "nodes" in obj and isinstance(obj["nodes"], list):
            obj["nodes"] = patch_node_images(case_id, obj["nodes"])
        board = LinkBoard.model_validate({"stage": stage, **obj})
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"agent_invalid_json:{e}")

    return board


@api_router.post("/cases/{case_id}/chat", response_model=ChatResponse)
async def api_chat(case_id: str, req: ChatRequest) -> ChatResponse:
    _require_case(case_id)
    try:
        return await gradient_chat(case_id, req)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SESSION-BASED ENGINE ENDPOINTS — investigation gates, triggers, contradictions
# ══════════════════════════════════════════════════════════════════════════════

class CreateSessionRequest(BaseModel):
    case_id: str

class CreateSessionResponse(BaseModel):
    session_id: str
    case_id: str
    discovered_entities: list[str]

class SessionBoardResponse(BaseModel):
    session_id: str
    case_id: str
    stage: int
    stage_name: str
    can_advance: bool
    nodes: list[dict]
    edges: list[dict]
    newly_unlocked: list[dict]
    contradictions: list[dict]

class SessionChatRequest(BaseModel):
    message: str
    role: str = "co_detective"
    persona_id: str | None = None

class SessionChatResponse(BaseModel):
    reply: str
    role: str
    newly_unlocked: list[dict]
    contradictions: list[dict]

class PresentEvidenceRequest(BaseModel):
    evidence_id: str
    suspect_id: str

class ConcludeRequest(BaseModel):
    killer: str
    motive: str
    method: str = ""

class ConcludeResponse(BaseModel):
    score: int
    max_score: int
    percentage: int
    feedback: str
    official_verdict: str
    entities_discovered: int
    total_entities: int


@api_router.post("/sessions", response_model=CreateSessionResponse)
async def api_create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new investigation session for a case."""
    _require_case(req.case_id)
    state = await create_session(req.case_id)
    inv_engine.get_visible_entities(state)  # populate start entities
    await save_session(state)
    return CreateSessionResponse(
        session_id=state.session_id,
        case_id=state.case_id,
        discovered_entities=sorted(state.discovered_entities),
    )


@api_router.get("/sessions/{session_id}/board", response_model=SessionBoardResponse)
async def api_session_board(session_id: str) -> SessionBoardResponse:
    """Get investigation board — only shows discovered entities."""
    state = await _require_session(session_id)
    nodes = inv_engine.get_visible_entities(state)
    edges = inv_engine.get_visible_connections(state)
    nodes = patch_node_images(state.case_id, nodes)
    contradictions = inv_engine.check_contradictions(state)
    advance_check = inv_engine.can_advance_stage(state)
    
    # Save session because get_visible_entities and check_contradictions may have updated discovery state
    await save_session(state)
    
    return SessionBoardResponse(
        session_id=state.session_id,
        case_id=state.case_id,
        stage=state.stage,
        stage_name=STAGE_NAMES.get(state.current_stage, "Stage " + str(state.current_stage)),
        can_advance=advance_check["can_advance"],
        nodes=nodes,
        edges=edges,
        newly_unlocked=[],
        contradictions=contradictions,
    )


@api_router.post("/sessions/{session_id}/chat", response_model=SessionChatResponse)
async def api_session_chat(session_id: str, req: SessionChatRequest) -> SessionChatResponse:
    """Chat with engine-restricted AI. Player messages trigger evidence unlocks."""
    state = await _require_session(session_id)
    client = _get_client(state.case_id)

    # 1. Process triggers
    newly_unlocked = inv_engine.process_chat_triggers(req.message, state)

    # 2. Build restricted context with stage knowledge boundary injected
    stage_prefix = build_stage_prefix(state)
    engine_context = inv_engine.build_ai_context(state, req.role, req.persona_id)

    # 3. Assemble messages — persona-specific history only
    persona_history = state.get_persona_history(req.role, req.persona_id, limit=10)
    messages = [{"role": "system", "content": stage_prefix + engine_context}]
    for msg in persona_history:
        messages.append(msg)
    messages.append({
        "role": "user",
        "content": f"case_id={state.case_id}\n\nDetective's message:\n{req.message}",
    })

    # 4. Call AI
    resp = await client.chat_completions(
        messages=messages,
        include_retrieval_info=True,
        include_guardrails_info=True,
    )
    reply = client.extract_content(resp).strip()

    # 5. Update state
    state.add_chat("user", req.message, req.persona_id, req.role)
    state.add_chat("assistant", reply, req.persona_id, req.role)
    if req.persona_id:
        state.interrogated_characters.add(req.persona_id)

    # 6. Check contradictions
    contradictions = inv_engine.check_contradictions(state)

    await save_session(state)

    return SessionChatResponse(
        reply=reply,
        role=req.role,
        newly_unlocked=[{"id": e["id"], "name": e["name"], "type": e["type"]} for e in newly_unlocked],
        contradictions=contradictions,
    )


@api_router.post("/sessions/{session_id}/present-evidence", response_model=SessionChatResponse)
async def api_present_evidence(session_id: str, req: PresentEvidenceRequest) -> SessionChatResponse:
    """Present evidence to a suspect. If it contradicts their claim, AI responds under pressure."""
    state = await _require_session(session_id)
    client = _get_client(state.case_id)
    schema = load_schema(state.case_id)

    from app.engine.schema import get_entity, get_character

    evidence = get_entity(schema, req.evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="evidence_not_found")
    if req.evidence_id not in state.evidence_collected and req.evidence_id not in state.discovered_entities:
        raise HTTPException(status_code=400, detail="evidence_not_yet_discovered")

    char = get_character(schema, req.suspect_id)
    confrontation_prompt = ""
    if char:
        for c in char.get("contradictions", []):
            if c["contradicted_by"] == req.evidence_id:
                confrontation_prompt = c["confrontation_prompt"]
                state.contradictions_found.add(c["id"])
                break

    engine_context = inv_engine.build_ai_context(state, "suspect", req.suspect_id)
    pressure = (
        f"\n\n🔴 EVIDENCE PRESENTED: {evidence['name']}\n{evidence['description']}\n"
    )
    if confrontation_prompt:
        pressure += f"\nCONFRONTATION: {confrontation_prompt}\nBecome defensive but slowly reveal more."
    else:
        pressure += "\nThe detective is showing you this evidence. React in character."

    persona_history = state.get_persona_history("suspect", req.suspect_id, limit=10)
    messages = [
        {"role": "system", "content": engine_context + pressure},
    ]
    for msg in persona_history:
        messages.append(msg)
    messages.append({"role": "user", "content": f"I'm presenting this evidence: {evidence['name']}. What do you say?"})

    resp = await client.chat_completions(messages=messages, include_retrieval_info=True)
    reply = client.extract_content(resp).strip()

    state.add_chat("user", f"[Presented evidence: {evidence['name']}]", req.suspect_id, "suspect")
    state.add_chat("assistant", reply, req.suspect_id, "suspect")

    contradictions = inv_engine.check_contradictions(state)
    await save_session(state)
    return SessionChatResponse(
        reply=reply,
        role="suspect",
        newly_unlocked=[],
        contradictions=contradictions,
    )


@api_router.get("/sessions/{session_id}/contradictions")
async def api_get_contradictions(session_id: str):
    state = await _require_session(session_id)
    new_contradictions = inv_engine.check_contradictions(state)
    await save_session(state)
    return {
        "contradictions_found": sorted(state.contradictions_found),
        "new_contradictions": new_contradictions,
    }


@api_router.get("/sessions/{session_id}/timeline", response_model=TimelineResponse)
async def api_get_timeline(session_id: str) -> TimelineResponse:
    """Get chronological investigation events."""
    state = await _require_session(session_id)
    return TimelineResponse(
        session_id=state.session_id,
        events=[TimelineEventModel(**vars(e)) for e in state.timeline]
    )


@api_router.post("/sessions/{session_id}/conclude", response_model=ConcludeResponse)
async def api_conclude(session_id: str, req: ConcludeRequest) -> ConcludeResponse:
    """Submit final deduction and get scored."""
    state = await _require_session(session_id)
    result = inv_engine.evaluate_conclusion(state, req.model_dump())
    await save_session(state)
    return ConcludeResponse(**result)


@api_router.post("/sessions/{session_id}/gate")
async def api_satisfy_gate(session_id: str, gate_name: str):
    """Manually satisfy an investigation gate."""
    state = await _require_session(session_id)
    newly_visible = inv_engine.satisfy_gate(gate_name, state)
    await save_session(state)
    return {
        "gate": gate_name,
        "newly_unlocked": [{"id": e["id"], "name": e["name"], "type": e["type"]} for e in newly_visible],
    }


# ── Stage management endpoints ────────────────────────────────────────────────

class StageResponse(BaseModel):
    current_stage: int
    stage_name: str
    stage_description: str
    completed_stages: list[int]
    can_advance: bool
    requirements_met: dict

class StageAdvanceResponse(BaseModel):
    advanced: bool
    new_stage: int
    stage_name: str
    stage_description: str
    newly_unlocked_entities: list[dict]
    graph_event: str


@api_router.get("/sessions/{session_id}/stage", response_model=StageResponse)
async def api_get_stage(session_id: str) -> StageResponse:
    """Get current investigation stage info and whether player can advance."""
    state = await _require_session(session_id)
    advance_check = inv_engine.can_advance_stage(state)
    return StageResponse(
        current_stage=state.current_stage,
        stage_name=STAGE_NAMES.get(state.current_stage, f"Stage {state.current_stage}"),
        stage_description=STAGE_DESCRIPTIONS.get(state.current_stage, ""),
        completed_stages=state.completed_stages,
        can_advance=advance_check["can_advance"],
        requirements_met=advance_check.get("requirements_met", {}),
    )


@api_router.post("/sessions/{session_id}/stage/advance", response_model=StageAdvanceResponse)
async def api_advance_stage(session_id: str) -> StageAdvanceResponse:
    """Advance to the next investigation stage."""
    state = await _require_session(session_id)
    check = inv_engine.can_advance_stage(state)
    if not check["can_advance"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Complete current stage requirements before advancing.",
                "requirements_met": check.get("requirements_met", {}),
                "current_stage": state.current_stage,
            },
        )
    result = inv_engine.advance_stage(state)
    if not result.get("advanced"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Cannot advance"))
    
    await save_session(state)
    return StageAdvanceResponse(**result)


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH ENDPOINTS — knowledge graph / pinboard system
# ══════════════════════════════════════════════════════════════════════════════

@api_router.get("/cases/{case_id}/graph")
async def get_case_graph(case_id: str, background_tasks: BackgroundTasks) -> dict:
    """Return full case graph. Returns static layer immediately; triggers AI enrichment in background."""
    _require_case(case_id)
    cached = get_cached_graph(case_id)
    if cached:
        return {"status": "ready", "graph": cached}

    # Return static-only immediately so the frontend isn't blocked
    static_only = merge_graph_with_schema(case_id, {"nodes": [], "edges": []})

    if not is_graph_building(case_id):
        background_tasks.add_task(_build_and_cache_graph, case_id)

    return {"status": "building", "graph": static_only}


async def _build_and_cache_graph(case_id: str) -> None:
    """Background task: call AI agents, merge with schema, cache to memory + disk."""
    set_graph_building(case_id, True)
    try:
        ai_graph = await build_full_case_graph(case_id)
        merged = merge_graph_with_schema(case_id, ai_graph)
        set_cached_graph(case_id, merged)
        print(f"[graph] Built and cached graph for {case_id}: "
              f"{len(merged['nodes'])} nodes, {len(merged['edges'])} edges")
        # Persist to disk so the next startup skips re-building
        schema_dir = os.path.join(os.path.dirname(__file__), "data", "case_schemas")
        out_path = os.path.join(schema_dir, f"{case_id}-graph.json")
        try:
            with open(out_path, "w") as f:
                json.dump(merged, f, indent=2)
            print(f"[graph] Persisted to {out_path}")
        except Exception as e:
            print(f"[graph] Could not persist graph to disk: {e}")
    except Exception as e:
        print(f"[graph] Build failed for {case_id}: {e}")
    finally:
        set_graph_building(case_id, False)


@api_router.get("/sessions/{session_id}/graph")
async def get_session_graph(session_id: str) -> dict:
    """Return session-filtered graph — respects the player's current unlock progress."""
    state = await _require_session(session_id)
    case_id = state.case_id

    full_graph = get_cached_graph(case_id) or \
                 merge_graph_with_schema(case_id, {"nodes": [], "edges": []})

    # Derive player level from how many gates have been satisfied
    unlocked_gates = getattr(state, "satisfied_gates", set())
    player_level = min(5, 1 + len(unlocked_gates))

    visible_nodes: list[dict] = []
    for node in full_graph["nodes"]:
        lvl = node.get("unlock_level", 1)
        if lvl <= player_level:
            visible_nodes.append({**node, "locked": False})
        elif lvl == player_level + 1:
            # Tease — show it exists but hide all content
            visible_nodes.append({
                "id": node["id"],
                "label": "???",
                "type": node.get("type", "UNKNOWN"),
                "locked": True,
                "unlock_level": lvl,
            })
        # Nodes beyond player_level+1 are fully hidden

    unlocked_ids = {n["id"] for n in visible_nodes if not n.get("locked")}
    visible_edges = [
        e for e in full_graph["edges"]
        if e.get("source") in unlocked_ids
        and e.get("target") in unlocked_ids
        and e.get("unlock_level", 1) <= player_level
    ]

    return {
        "graph": {"nodes": visible_nodes, "edges": visible_edges},
        "player_level": player_level,
        "max_level": 5,
        "graph_status": "ready" if get_cached_graph(case_id) else "building",
    }


@api_router.post("/sessions/{session_id}/graph/node-unlocked")
async def notify_node_unlocked(session_id: str, payload: dict) -> dict:
    """
    Called by the frontend when a keyword trigger fires.
    Returns the delta — newly visible node + its edges — so the UI can animate them in.
    """
    state = await _require_session(session_id)
    newly_unlocked_id = payload.get("entity_id")

    full_graph = get_cached_graph(state.case_id) or \
                 merge_graph_with_schema(state.case_id, {"nodes": [], "edges": []})

    new_node = next(
        (n for n in full_graph["nodes"] if n["id"] == newly_unlocked_id), None
    )
    new_edges = [
        e for e in full_graph["edges"]
        if e.get("source") == newly_unlocked_id
        or e.get("target") == newly_unlocked_id
    ]
    return {"new_node": new_node, "new_edges": new_edges}


# ── Persistence Endpoints for Frontend (Notes & Graph State) ─────────────────

class NotesRequest(BaseModel):
    notes: str

class GraphStateRequest(BaseModel):
    graph_state: dict

@api_router.get("/sessions/{session_id}/notes")
async def api_get_notes(session_id: str):
    state = await _require_session(session_id)
    return {"notes": state.notes}

@api_router.post("/sessions/{session_id}/notes")
async def api_save_notes(session_id: str, req: NotesRequest):
    state = await _require_session(session_id)
    state.notes = req.notes
    await save_session(state)
    return {"status": "saved"}

@api_router.get("/sessions/{session_id}/graph-state")
async def api_get_graph_state(session_id: str):
    state = await _require_session(session_id)
    return {"graph_state": state.graph_state}

@api_router.post("/sessions/{session_id}/graph-state")
async def api_save_graph_state(session_id: str, req: GraphStateRequest):
    state = await _require_session(session_id)
    state.graph_state = req.graph_state
    await save_session(state)
    return {"status": "saved"}


app.include_router(api_router)         # Handles DO's Path Trimmed requests
app.include_router(api_router, prefix="/api")  # Handles local explicit /api requests
