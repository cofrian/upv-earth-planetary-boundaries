from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models.ingestion_event import IngestionEvent
from app.db.models.paper import Paper
from app.db.models.pb_result import PBResult
from app.db.session import get_db
from app.repositories.job_repository import JobRepository
from app.schemas.analytics import SimilarPaper
from app.schemas.job import (
    AbstractValidation,
    EmbeddingInfo,
    JobEventOut,
    JobOut,
    JobResultOut,
)
from app.schemas.paper import PBResultOut
from app.services.embedding_service.service import get_active_model_info
from app.services.similarity_search.service import find_similar_for_text
from app.services.summarization.service import summarize_abstract

router = APIRouter()


def _build_job_out(job) -> JobOut:
    return JobOut(
        id=job.id,
        paper_id=job.paper_id,
        filename_original=job.filename_original,
        status=job.status,
        stage=job.stage,
        progress_pct=job.progress_pct,
        error_code=job.error_code,
        error_message=job.error_message,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobOut:
    jobs = JobRepository(db)
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return _build_job_out(job)


def _read_event_payload(db: Session, job_id, event_type: str) -> dict | None:
    event = (
        db.query(IngestionEvent)
        .filter(IngestionEvent.job_id == job_id, IngestionEvent.event_type == event_type)
        .order_by(IngestionEvent.created_at.desc())
        .first()
    )
    if not event:
        return None
    return event.event_payload or {}


@router.get("/{job_id}/result", response_model=JobResultOut)
def get_job_result(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobResultOut:
    jobs = JobRepository(db)
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    job_out = _build_job_out(job)

    if not job.paper_id:
        return JobResultOut(job=job_out)

    paper = job.paper
    pb = (
        db.query(PBResult)
        .filter(PBResult.paper_id == job.paper_id)
        .order_by(PBResult.created_at.desc())
        .first()
    )
    pb_out = None
    if pb:
        pb_out = PBResultOut(
            top_pb_code=pb.top_pb_code,
            top_pb_score=pb.top_pb_score,
            secondary_pbs=pb.secondary_pbs,
            score_map=pb.score_map,
            explanation_text=pb.explanation_text,
        )

    summary = summarize_abstract(paper.clean_abstract) if paper else None

    abstract_validation = None
    if paper:
        abstract_norm = paper.abstract_norm or ""
        abstract_char_len = len(abstract_norm)
        passes = abstract_char_len > 500
        abstract_validation = AbstractValidation(
            abstract_detected=abstract_char_len > 0,
            abstract_char_len=abstract_char_len,
            threshold=500,
            passes_threshold=passes,
            is_valid_for_embedding=passes,
        )

    embedding_payload = _read_event_payload(db, job.id, "generate_embedding") or {}
    active = get_active_model_info()
    embedding_text_preview = None
    if paper:
        text = f"{paper.title or ''} {paper.abstract_norm or ''}".strip()
        embedding_text_preview = text[:280] + ("..." if len(text) > 280 else "")
    embedding_info = EmbeddingInfo(
        model_id=str(embedding_payload.get("model_id", active.model_id)),
        family=active.family,
        is_specter=bool(embedding_payload.get("is_specter", active.is_specter)),
        embedding_dim=int(embedding_payload.get("embedding_dim", active.dimension or 0) or 0) or None,
        embedding_text_rule="title + clean_abstract_semantic",
        embedding_text_preview=embedding_text_preview,
        fallback_used=bool(embedding_payload.get("fallback_used", active.fallback_used)),
    )

    similar_payload = _read_event_payload(db, job.id, "similar_papers_snapshot") or {}
    raw_items: list[dict] = list(similar_payload.get("items") or [])
    if not raw_items and paper and abstract_validation and abstract_validation.is_valid_for_embedding:
        text = f"{paper.title or ''} {paper.abstract_norm or ''}".strip()
        if text:
            try:
                raw_items = list(find_similar_for_text(text, top_k=8))
            except Exception:  # noqa: BLE001
                raw_items = []

    # Enriquecer con paper_id (UUID) para enlazar al análisis interno
    if raw_items:
        doc_ids = [item.get("doc_id") for item in raw_items if item.get("doc_id")]
        rows = db.query(Paper.id, Paper.doc_id).filter(Paper.doc_id.in_(doc_ids)).all() if doc_ids else []
        lookup = {doc_id: str(paper_id) for paper_id, doc_id in rows}
        for item in raw_items:
            item.setdefault("paper_id", lookup.get(item.get("doc_id")))

    similar_papers: list[SimilarPaper] = []
    for item in raw_items:
        try:
            similar_papers.append(SimilarPaper(**item))
        except Exception:  # noqa: BLE001
            continue

    return JobResultOut(
        job=job_out,
        abstract_detected=paper.abstract_norm if paper else None,
        abstract_validation=abstract_validation,
        embedding_info=embedding_info,
        summary=summary,
        pb_result=pb_out,
        similar_papers=similar_papers,
    )


@router.get("/{job_id}/events", response_model=list[JobEventOut])
def list_job_events(job_id: uuid.UUID, limit: int = 200, db: Session = Depends(get_db)) -> list[JobEventOut]:
    jobs = JobRepository(db)
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    safe_limit = max(1, min(limit, 1000))
    events = jobs.list_events(job_id, limit=safe_limit)
    return [
        JobEventOut(
            id=event.id,
            job_id=event.job_id,
            event_type=event.event_type,
            event_payload=event.event_payload,
            created_at=event.created_at,
        )
        for event in events
    ]
