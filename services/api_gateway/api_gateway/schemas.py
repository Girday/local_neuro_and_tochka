from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    username: str
    display_name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    tenant_id: str


class AssistantContext(BaseModel):
    channel: Optional[str] = None
    ui_session_id: Optional[str] = None
    conversation_id: Optional[str] = None


class AssistantQueryRequest(BaseModel):
    query: str
    language: Optional[str] = Field(default="ru")
    context: Optional[AssistantContext] = None


class AssistantSource(BaseModel):
    doc_id: str
    doc_title: Optional[str] = None
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class AssistantResponseMeta(BaseModel):
    latency_ms: Optional[int] = None
    trace_id: str
    safety: Optional[dict[str, Any]] = None


class AssistantResponse(BaseModel):
    answer: str
    sources: List[AssistantSource] = Field(default_factory=list)
    meta: AssistantResponseMeta


class DocumentItem(BaseModel):
    doc_id: str
    name: str
    status: str
    product: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentDetail(DocumentItem):
    pages: Optional[int] = None
    sections: Optional[List[dict[str, Any]]] = None


class DocumentUploadResponse(BaseModel):
    doc_id: str
    status: str


class ErrorDetails(BaseModel):
    code: str
    message: str
    trace_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class SafetyCheckResult(BaseModel):
    status: str = Field(description="allowed / blocked")
    reason: Optional[str] = None
