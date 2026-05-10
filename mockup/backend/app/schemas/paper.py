from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class PBResultOut(BaseModel):
    top_pb_code: str
    top_pb_score: float
    secondary_pbs: list[dict] | dict
    score_map: dict
    explanation_text: str


class PaperOut(BaseModel):
    id: uuid.UUID
    doc_id: str | None
    title: str
    abstract_norm: str
    year: int | None
    doi: str | None
    source: str | None
    journal: str | None
    keywords: str | None
    created_at: datetime | None
    pb_result: PBResultOut | None = None
    abstract_char_len: int = 0
    is_valid_for_embedding: bool = False


class PaperListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PaperOut]
