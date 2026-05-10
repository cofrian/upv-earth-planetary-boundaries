from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.analytics import SimilarPaper
from app.schemas.paper import PBResultOut


class JobOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID | None
    filename_original: str
    status: str
    stage: str
    progress_pct: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class AbstractValidation(BaseModel):
    abstract_detected: bool
    abstract_char_len: int
    threshold: int = 500
    passes_threshold: bool
    is_valid_for_embedding: bool


class EmbeddingInfo(BaseModel):
    model_id: str
    family: str
    is_specter: bool
    embedding_dim: int | None
    embedding_text_rule: str
    embedding_text_preview: str | None = None
    fallback_used: bool = False


class JobResultOut(BaseModel):
    job: JobOut
    abstract_detected: str | None = None
    abstract_validation: AbstractValidation | None = None
    embedding_info: EmbeddingInfo | None = None
    summary: str | None = None
    pb_result: PBResultOut | None = None
    similar_papers: list[SimilarPaper] = []


class JobEventOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    event_type: str
    event_payload: dict
    created_at: datetime | None
