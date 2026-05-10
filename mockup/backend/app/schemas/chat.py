from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Cuerpo de la petición al chatbot.

    `paper_id` y `job_id` son opcionales y mutuamente sustituibles; si se
    incluyen, el context_builder añade el paper analizado al pack.
    """

    question: str = Field(min_length=1, max_length=2000)
    paper_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    include_analytics: bool = True


class ChatContextSummary(BaseModel):
    has_paper: bool = False
    has_pb_result: bool = False
    similar_count: int = 0
    pb_catalog_count: int = 0
    methodology_count: int = 0
    has_analytics: bool = False
    paper_title: str | None = None


class ChatResponse(BaseModel):
    enabled: bool
    available: bool
    text: str
    error: str | None = None
    model: str | None = None
    duration_sec: float | None = None
    context: ChatContextSummary


class ChatHealth(BaseModel):
    enabled: bool
    available: bool
    model: str | None = None
    base_url: str | None = None
    reason: str | None = None
