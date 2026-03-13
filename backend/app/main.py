from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import ValidationError

from app.data.cases import list_cases, get_case_ids
from app.data.images import patch_node_images
from app.models import CaseDetail, CaseListItem, CaseIntroSlide, ChatRequest, ChatResponse, LinkBoard
from app.services.chat import gradient_chat
from app.services.do_agent import DOAgentClient


load_dotenv()

app = FastAPI(title="IAM Detective API", version="0.2.0")

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_case(case_id: str) -> None:
    """Raise 404 if case_id is not in the registry."""
    if case_id not in get_case_ids():
        raise HTTPException(status_code=404, detail=f"case_not_found:{case_id}")


def _get_client(case_id: str) -> DOAgentClient:
    try:
        return DOAgentClient(case_id=case_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cases", response_model=list[CaseListItem])
def api_list_cases() -> list[CaseListItem]:
    return list_cases()


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
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


@app.get("/api/cases/{case_id}/intro", response_model=list[CaseIntroSlide])
async def api_get_intro_slides(case_id: str) -> list[CaseIntroSlide]:
    """Returns 3-4 cinematic story slides for the case introduction screen."""
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
                    "Each object in the array has exactly these keys: "
                    "\"page\" (integer, 1 to 4), "
                    "\"text\" (string, 2-4 sentences written like a noir thriller — atmospheric, factual, dark), "
                    "\"image_prompt\" (string, short comma-separated description for a dark background image). "
                    "Slide 1: Time, place, and first discovery. "
                    "Slide 2: Key facts of the crime. "
                    "Slide 3: What remains unknown — the mystery. "
                    "Slide 4: The investigation begins — end on a hook. "
                    "Return ONLY the JSON object. No extra text, no markdown, no explanation."
                ),
            },
            {"role": "user", "content": f"case_id={case_id}\nGenerate the 4 cinematic intro slides as JSON."},
        ],
        include_retrieval_info=True,
    )

    content = client.extract_content(resp).strip()
    try:
        # Primary: agent returns {"slides": [...]}
        obj = client.extract_json_object(content)
        slides_raw = obj.get("slides") or obj.get("intro_slides") or obj.get("pages")

        # Fallback: agent returned a bare array
        if slides_raw is None:
            slides_raw = client.extract_json_array(content)

        if not isinstance(slides_raw, list):
            raise ValueError("slides_key_not_a_list")

        slides = [CaseIntroSlide.model_validate(s) for s in slides_raw]
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"agent_invalid_json:{e}")

    return slides


@app.get("/api/cases/{case_id}/linkboard", response_model=LinkBoard)
async def api_get_linkboard(case_id: str, stage: int = 1) -> LinkBoard:
    _require_case(case_id)
    client = _get_client(case_id)

    # Wikipedia article hints per case for image retrieval
    _WIKI_HINTS: dict[str, str] = {
        "aarushi-talwar": (
            "Wikipedia sources include: https://en.wikipedia.org/wiki/Aarushi_Talwar_murder_case "
            "and https://en.wikipedia.org/wiki/Aarushi_Talwar . "
            "Image URLs from Wikimedia Commons are available (format: https://upload.wikimedia.org/wikipedia/...)."
        ),
        "oj-simpson": (
            "Wikipedia sources include: https://en.wikipedia.org/wiki/O._J._Simpson_murder_case "
            "and https://en.wikipedia.org/wiki/O._J._Simpson . "
            "Image URLs from Wikimedia Commons are available (format: https://upload.wikimedia.org/wikipedia/...)."
        ),
        "zodiac-killer": (
            "Wikipedia sources include: https://en.wikipedia.org/wiki/Zodiac_Killer . "
            "Image URLs from Wikimedia Commons are available if referenced in the knowledge base."
        ),
    }
    wiki_hint = _WIKI_HINTS.get(case_id, "")

    stage = max(1, min(int(stage), 5))
    resp = await client.chat_completions(
        messages=[
            {
                "role": "system",
                "content": (
                    f"You generate a link-board graph for detective workspace for case: {case_id}. "
                    "Use ONLY the attached knowledge base for this case. "
                    f"{wiki_hint} "
                    "Return ONLY valid JSON with keys: nodes, edges. "
                    "nodes: array of objects, each with: "
                    "  id (string slug), "
                    "  type (one of: suspect, victim, witness, evidence, location, event), "
                    "  name (string), "
                    "  description (string, 1-2 sentences of factual detail), "
                    "  image_url (string or null — if this node is a real person or place and a Wikipedia/Wikimedia "
                    "  Commons image URL is available from the knowledge base, include the FULL direct image URL "
                    "  e.g. https://upload.wikimedia.org/wikipedia/commons/... Otherwise null.), "
                    "  revealed_at_stage (integer 1-5). "
                    "edges: array of objects, each with: from (node id), to (node id), label (string), revealed_at_stage (integer 1-5). "
                    f"Only include items with revealed_at_stage <= {stage}. "
                    "Do not invent names or image URLs. Use 'Unknown' if a name is not in the knowledge base."
                ),
            },
            {"role": "user", "content": f"case_id={case_id}\nstage={stage}\nGenerate link-board JSON with image URLs where available."},
        ],
        include_retrieval_info=True,
    )

    content = client.extract_content(resp)
    try:
        obj = client.extract_json_object(content)
        # Patch in known Wikimedia images before validation
        if "nodes" in obj and isinstance(obj["nodes"], list):
            obj["nodes"] = patch_node_images(case_id, obj["nodes"])
        board = LinkBoard.model_validate({"stage": stage, **obj})
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"agent_invalid_json:{e}")

    return board


@app.post("/api/cases/{case_id}/chat", response_model=ChatResponse)
async def api_chat(case_id: str, req: ChatRequest) -> ChatResponse:
    _require_case(case_id)
    try:
        return await gradient_chat(case_id, req)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
