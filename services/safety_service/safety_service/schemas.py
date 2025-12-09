from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SafetyUser(BaseModel):
    user_id: str
    tenant_id: str
    roles: Optional[List[str]] = None
    locale: Optional[str] = None


class SafetyMeta(BaseModel):
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    trace_id: Optional[str] = None


class SafetyContext(BaseModel):
    conversation_id: Optional[str] = None
    ui_session_id: Optional[str] = None


class InputCheckRequest(BaseModel):
    user: SafetyUser
    query: str
    channel: Optional[str] = None
    context: Optional[SafetyContext] = None
    meta: Optional[SafetyMeta] = None


class SafetyResponse(BaseModel):
    status: str = Field(description="allowed/transformed/blocked")
    reason: Optional[str] = None
    message: Optional[str] = None
    risk_tags: List[str] = Field(default_factory=list)
    transformed_query: Optional[str] = None
    transformed_answer: Optional[str] = None
    policy_id: Optional[str] = None
    trace_id: Optional[str] = None


class SourceItem(BaseModel):
    doc_id: Optional[str] = None
    section_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class OutputCheckRequest(BaseModel):
    user: SafetyUser
    query: str
    answer: str
    sources: Optional[List[SourceItem]] = None
    meta: Optional[SafetyMeta] = None
    context: Optional[SafetyContext] = None
