from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CaseStatus = Literal["solved", "unsolved", "pending"]


class CaseListItem(BaseModel):
    id: str
    title: str
    subtitle: str
    status: CaseStatus
    hero_image_url: str | None = None


class CaseDetail(BaseModel):
    id: str
    title: str
    status: CaseStatus
    opening_lines: list[str] = Field(default_factory=list)
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
    nodes: list[LinkNode]
    edges: list[LinkEdge]


ChatRole = Literal["co_detective", "witness"]


class ChatRequest(BaseModel):
    role: ChatRole = "co_detective"
    message: str
    stage: int = 1


class ChatResponse(BaseModel):
    role: ChatRole
    reply: str
    stage_suggestion: int | None = None

