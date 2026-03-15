from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CaseStatus = Literal["solved", "unsolved", "pending"]
CaseDifficulty = Literal["easy", "medium", "hard"]


class CaseListItem(BaseModel):
    id: str
    title: str
    subtitle: str
    status: CaseStatus
    year: int | None = None
    location: str | None = None
    difficulty: CaseDifficulty | None = None
    hero_image_url: str | None = None


class CaseIntroSlide(BaseModel):
    page: int
    text: str
    image_prompt: str | None = None  # used by frontend for background mood


class CaseDetail(BaseModel):
    id: str
    title: str
    status: CaseStatus
    year: int | None = None
    location: str | None = None
    opening_lines: list[str] = Field(default_factory=list)
    intro_slides: list[CaseIntroSlide] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class LinkNode(BaseModel):
    id: str
    # Free-form type string so the agent can return domain terms like
    # "case", "crime scene", etc. Frontend just displays it.
    type: str
    name: str
    description: str
    image_url: str | None = None
    revealed_at_stage: int = 1


class LinkEdge(BaseModel):
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    label: str
    revealed_at_stage: int = 1

    class Config:
        populate_by_name = True


class LinkBoard(BaseModel):
    stage: int
    nodes: list[LinkNode] = Field(default_factory=list)
    edges: list[LinkEdge] = Field(default_factory=list)


ChatRole = Literal["co_detective", "witness", "suspect"]


class ChatRequest(BaseModel):
    role: ChatRole = "co_detective"
    message: str
    stage: int = 1
    persona_id: str | None = None  # e.g. "witness-jane-doe" or "suspect-allen"


class ChatResponse(BaseModel):
    role: ChatRole
    reply: str
    stage_suggestion: int | None = None


class TimelineEventModel(BaseModel):
    id: str
    timestamp: str
    type: str
    title: str
    description: str
    stage: int
    meta: dict = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    session_id: str
    events: list[TimelineEventModel]
