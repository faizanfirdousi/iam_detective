from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import ValidationError

from app.data.cases import list_cases
from app.models import CaseDetail, CaseListItem, ChatRequest, ChatResponse, LinkBoard
from app.services.chat import gradient_chat
from app.services.do_agent import DOAgentClient


load_dotenv()

app = FastAPI(title="IAM Detective API", version="0.1.0")

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cases", response_model=list[CaseListItem])
def api_list_cases() -> list[CaseListItem]:
    return list_cases()


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
async def api_get_case(case_id: str) -> CaseDetail:
    try:
        client = DOAgentClient()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Ask the Gradient agent to produce the opening in structured JSON (no invented facts).
    resp = await client.chat_completions(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are generating a detective game 'case intro' using ONLY the attached knowledge base. "
                    "Return ONLY valid JSON with keys: title (string), status (solved|unsolved|pending), "
                    "opening_lines (array of short strings), sources (array of source filenames/urls if available). "
                    "Do not include any extra keys. If unsure, keep opening_lines minimal."
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


@app.get("/api/cases/{case_id}/linkboard", response_model=LinkBoard)
async def api_get_linkboard(case_id: str, stage: int = 1) -> LinkBoard:
    try:
        client = DOAgentClient()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    stage = max(1, min(int(stage), 5))
    resp = await client.chat_completions(
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate a link-board graph for a detective workspace using ONLY the attached knowledge base. "
                    "Return ONLY valid JSON with keys: nodes, edges. "
                    "nodes: [{id,type,name,description,image_url?,revealed_at_stage}]. "
                    "edges: [{from,to,label,revealed_at_stage}]. "
                    "Constraints: revealed_at_stage is integer 1-5. "
                    f"Only include items with revealed_at_stage <= {stage}. "
                    "Do not invent names; if needed use 'Unknown' with cautious descriptions."
                ),
            },
            {"role": "user", "content": f"case_id={case_id}\nstage={stage}\nGenerate link-board JSON."},
        ],
        include_retrieval_info=True,
    )

    content = client.extract_content(resp)
    try:
        obj = client.extract_json_object(content)
        board = LinkBoard.model_validate({"stage": stage, **obj})
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"agent_invalid_json:{e}")

    return board


@app.post("/api/cases/{case_id}/chat", response_model=ChatResponse)
async def api_chat(case_id: str, req: ChatRequest) -> ChatResponse:
    try:
        return await gradient_chat(case_id, req)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

