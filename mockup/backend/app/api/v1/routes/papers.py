from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models.paper import Paper
from app.db.session import get_db
from app.repositories.paper_repository import PaperRepository
from app.schemas.analytics import SimilarPaper
from app.schemas.paper import PaperListResponse, PaperOut, PBResultOut
from app.services.similarity_search.service import find_similar_for_text

router = APIRouter()


def _enrich_with_paper_ids(items: list[dict], db: Session) -> list[dict]:
    """Resuelve doc_id → paper_id y refresca título desde la BD.

    Los títulos del meta precomputed pueden estar desactualizados respecto
    a la BD (p. ej. tras un saneamiento). Aquí los pisamos con el valor
    canónico almacenado en la tabla `papers`.
    """
    if not items:
        return items
    doc_ids = [item.get("doc_id") for item in items if item.get("doc_id")]
    if not doc_ids:
        return items
    rows = (
        db.query(Paper.id, Paper.doc_id, Paper.title)
        .filter(Paper.doc_id.in_(doc_ids))
        .all()
    )
    id_lookup = {doc_id: str(paper_id) for paper_id, doc_id, _ in rows}
    title_lookup = {doc_id: title for _, doc_id, title in rows if title}
    enriched = []
    for item in items:
        doc_id = item.get("doc_id")
        new_item = dict(item)
        new_item["paper_id"] = id_lookup.get(doc_id)
        if doc_id in title_lookup:
            new_item["title"] = title_lookup[doc_id]
        enriched.append(new_item)
    return enriched


def _to_paper_out(repo: PaperRepository, paper) -> PaperOut:
    pb = repo.get_latest_pb_result(paper.id)
    pb_out = None
    if pb:
        pb_out = PBResultOut(
            top_pb_code=pb.top_pb_code,
            top_pb_score=pb.top_pb_score,
            secondary_pbs=pb.secondary_pbs,
            score_map=pb.score_map,
            explanation_text=pb.explanation_text,
        )
    abstract_norm = paper.abstract_norm or ""
    abstract_char_len = len(abstract_norm)
    return PaperOut(
        id=paper.id,
        doc_id=paper.doc_id,
        title=paper.title,
        abstract_norm=abstract_norm,
        year=paper.year,
        doi=paper.doi,
        source=paper.source,
        journal=paper.journal,
        keywords=paper.keywords,
        created_at=paper.created_at,
        pb_result=pb_out,
        abstract_char_len=abstract_char_len,
        is_valid_for_embedding=abstract_char_len > 500,
    )


@router.get("", response_model=PaperListResponse)
def list_papers(
    query: str | None = None,
    year: int | None = None,
    max_year: int | None = Query(default=None, ge=1900, le=2100),
    journal: str | None = None,
    pb: str | None = None,
    doi: str | None = None,
    keywords: str | None = None,
    min_abstract_len: int | None = Query(default=None, ge=0, le=100000),
    only_embedding_valid: bool = Query(default=False),
    sort: str = Query(default="created_desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaperListResponse:
    repo = PaperRepository(db)
    effective_min = min_abstract_len
    if only_embedding_valid:
        effective_min = max(effective_min or 0, 501)
    items, total = repo.list_papers(
        query,
        year,
        max_year,
        journal,
        pb,
        doi,
        keywords,
        sort,
        page,
        page_size,
        min_abstract_len=effective_min,
    )
    return PaperListResponse(total=total, page=page, page_size=page_size, items=[_to_paper_out(repo, i) for i in items])


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: uuid.UUID, db: Session = Depends(get_db)) -> PaperOut:
    repo = PaperRepository(db)
    paper = repo.get_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return _to_paper_out(repo, paper)


@router.get("/{paper_id}/similar", response_model=list[SimilarPaper])
def get_similar_papers(
    paper_id: uuid.UUID,
    top_k: int = Query(default=8, ge=1, le=25),
    db: Session = Depends(get_db),
) -> list[SimilarPaper]:
    repo = PaperRepository(db)
    paper = repo.get_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper no encontrado")

    abstract = (paper.abstract_norm or "").strip()
    if len(abstract) <= 500:
        return []

    embedding_text = f"{paper.title or ''} {abstract}".strip()
    exclude = {paper.doc_id} if paper.doc_id else set()
    raw = find_similar_for_text(embedding_text, top_k=top_k, exclude_doc_ids=exclude)
    return [SimilarPaper(**item) for item in _enrich_with_paper_ids(raw, db)]
