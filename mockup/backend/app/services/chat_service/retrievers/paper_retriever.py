"""Recupera el contexto de un paper concreto (subido o de la BD).

Reutiliza `PaperRepository` para evitar reproducir SQL. Para los papers
similares usa `similarity_search.find_similar_for_text` ya cacheado en
memoria; el chatbot NO recalcula embeddings.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.paper_repository import PaperRepository

logger = logging.getLogger(__name__)


def _abstract_preview(text: str | None, max_chars: int = 800) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def fetch_paper_context(
    db: Session,
    paper_id: uuid.UUID,
    similar_top_k: int = 5,
) -> dict[str, Any] | None:
    """Devuelve el bloque de contexto del paper indicado.

    Estructura:
      - paper: metadatos canónicos
      - pb: top PB y secundarios con scores
      - similar: top-k vecinos con título/score/PB
    """
    repo = PaperRepository(db)
    paper = repo.get_by_id(paper_id)
    if not paper:
        return None

    pb = repo.get_latest_pb_result(paper_id)
    abstract = (paper.abstract_norm or "").strip()
    abstract_len = len(abstract)
    is_valid = abstract_len > 500

    similar: list[dict[str, Any]] = []
    if is_valid:
        try:
            from app.services.similarity_search.service import find_similar_for_text

            text = f"{paper.title or ''} {abstract}".strip()
            exclude = {paper.doc_id} if paper.doc_id else set()
            similar_raw = find_similar_for_text(text, top_k=similar_top_k, exclude_doc_ids=exclude)
            for item in similar_raw:
                similar.append(
                    {
                        "title": item.get("title"),
                        "year": item.get("year"),
                        "score": item.get("score"),
                        "pb_code": item.get("pb_code"),
                        "doi": item.get("doi"),
                        "abstract_preview": item.get("abstract_preview"),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("paper_retriever similar fallback: %s", exc)

    pb_block = None
    if pb:
        pb_block = {
            "top_pb_code": pb.top_pb_code,
            "top_pb_score": pb.top_pb_score,
            "secondary_pbs": pb.secondary_pbs,
            "score_map": pb.score_map,
            "explanation": pb.explanation_text,
        }

    return {
        "paper": {
            "id": str(paper.id),
            "doc_id": paper.doc_id,
            "title": paper.title,
            "year": paper.year,
            "journal": paper.journal,
            "doi": paper.doi,
            "keywords": paper.keywords,
            "abstract_char_len": abstract_len,
            "is_valid_for_embedding": is_valid,
            "abstract_preview": _abstract_preview(abstract),
        },
        "pb": pb_block,
        "similar": similar,
    }


def fetch_paper_context_by_job(
    db: Session,
    job_id: uuid.UUID,
    similar_top_k: int = 5,
) -> dict[str, Any] | None:
    """Igual que `fetch_paper_context` pero a partir del `job_id`."""
    from app.repositories.job_repository import JobRepository

    job = JobRepository(db).get_job(job_id)
    if not job or not job.paper_id:
        return None
    return fetch_paper_context(db, job.paper_id, similar_top_k=similar_top_k)
