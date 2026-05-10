import re
import uuid
from collections import Counter
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models.paper import Paper
from app.db.models.pb_result import PBResult

EXCLUDED_SOURCES = {"uploaded_pdf"}


def _normalize_source_label(source: str | None) -> str:
    if not source:
        return "Sin fuente"

    key = source.strip().lower()
    mapping = {
        "rclone_drive": "Repositorio institucional",
        "rclone": "Repositorio institucional",
        "uploaded_pdf": "Subidas manuales",
    }
    return mapping.get(key, source)


def _papers_base_query(db: Session):
    source_norm = func.lower(func.trim(func.coalesce(Paper.source, "")))
    return db.query(Paper).filter(
        ~or_(
            source_norm.in_(EXCLUDED_SOURCES),
            Paper.doc_id.like("upload-%"),
        )
    )


def overview(db: Session) -> dict:
    paper_q = _papers_base_query(db)
    total_papers = paper_q.with_entities(func.count(Paper.id)).scalar() or 0
    abstracts_valid = paper_q.filter(func.length(Paper.abstract_norm) > 0).with_entities(func.count(Paper.id)).scalar() or 0
    papers_classified = (
        # Mantenemos consistente el filtro con el resto del dashboard.
        db.query(func.count(PBResult.id))
        .join(Paper, PBResult.paper_id == Paper.id)
        .filter(
            ~or_(
                func.lower(func.trim(func.coalesce(Paper.source, ""))).in_(EXCLUDED_SOURCES),
                Paper.doc_id.like("upload-%"),
            )
        )
        .scalar()
        or 0
    )
    unique_journals = paper_q.with_entities(func.count(func.distinct(Paper.journal))).scalar() or 0
    avg_abstract_length = paper_q.with_entities(func.avg(func.length(Paper.abstract_norm))).scalar() or 0.0

    return {
        "total_papers": int(total_papers),
        "abstracts_valid": int(abstracts_valid),
        "papers_classified": int(papers_classified),
        "unique_journals": int(unique_journals),
        "avg_abstract_length": float(avg_abstract_length),
    }


def distribution_by_year(db: Session) -> list[dict]:
    max_dashboard_year = min(2024, datetime.now().year)
    rows = (
        _papers_base_query(db).with_entities(Paper.year, func.count(Paper.id))
        .filter(Paper.year.isnot(None))
        .filter(Paper.year.between(1900, max_dashboard_year))
        .group_by(Paper.year)
        .order_by(Paper.year.asc())
        .all()
    )
    return [{"label": str(year), "value": count} for year, count in rows]


def distribution_by_pb(db: Session) -> list[dict]:
    rows = (
        db.query(PBResult.top_pb_code, func.count(PBResult.id))
        .join(Paper, PBResult.paper_id == Paper.id)
        .filter(or_(Paper.source.is_(None), ~func.lower(Paper.source).in_(EXCLUDED_SOURCES)))
        .group_by(PBResult.top_pb_code)
        .order_by(func.count(PBResult.id).desc())
        .all()
    )
    return [{"label": pb, "value": count} for pb, count in rows]


def distribution_by_source(db: Session) -> list[dict]:
    rows = (
        _papers_base_query(db).with_entities(Paper.source, func.count(Paper.id))
        .filter(Paper.source.isnot(None))
        .group_by(Paper.source)
        .order_by(func.count(Paper.id).desc())
        .all()
    )
    aggregated: dict[str, int] = {}
    for source, count in rows:
        label = _normalize_source_label(source)
        aggregated[label] = aggregated.get(label, 0) + int(count)

    return [
        {"label": label, "value": value}
        for label, value in sorted(aggregated.items(), key=lambda item: item[1], reverse=True)
    ]


def distribution_by_abstract_length(db: Session) -> list[dict]:
    bins = [
        (0, 500, "0-500"),
        (501, 1000, "501-1000"),
        (1001, 1500, "1001-1500"),
        (1501, 3000, "1501-3000"),
        (3001, 100000, "3001+"),
    ]
    result: list[dict] = []
    for low, high, label in bins:
        count = (
            _papers_base_query(db)
            .filter(func.length(Paper.abstract_norm).between(low, high))
            .with_entities(func.count(Paper.id))
            .scalar()
            or 0
        )
        result.append({"label": label, "value": int(count)})
    return result


def _parse_keywords(raw_keywords: str | None) -> list[str]:
    if not raw_keywords:
        return []
    chunks = re.split(r"[,;|]", raw_keywords)
    keywords = [item.strip().lower() for item in chunks if item and item.strip()]
    return list(dict.fromkeys(keywords))


def _keyword_counter(papers: list[Paper]) -> Counter:
    counter: Counter = Counter()
    for paper in papers:
        for keyword in _parse_keywords(paper.keywords):
            counter[keyword] += 1
    return counter


def top_keywords_global(db: Session, limit: int = 20) -> list[dict]:
    papers = _papers_base_query(db).all()
    counts = _keyword_counter(papers)
    return [{"keyword": keyword, "value": value} for keyword, value in counts.most_common(limit)]


def top_keywords_by_pb(db: Session, pb_code: str, limit: int = 20) -> list[dict]:
    papers = (
        _papers_base_query(db)
        .join(PBResult, PBResult.paper_id == Paper.id)
        .filter(PBResult.top_pb_code == pb_code)
        .all()
    )
    counts = _keyword_counter(papers)
    return [{"keyword": keyword, "value": value} for keyword, value in counts.most_common(limit)]


def pb_temporal_evolution(db: Session) -> list[dict]:
    """Evolución temporal por Planetary Boundary.

    Devuelve, para cada combinación (top_pb_code, año válido), el conteo de
    papers en el corpus indexado.
    """
    rows = (
        _papers_base_query(db)
        .join(PBResult, PBResult.paper_id == Paper.id)
        .with_entities(PBResult.top_pb_code, Paper.year, func.count(Paper.id))
        .filter(Paper.year.isnot(None))
        .filter(Paper.year.between(1900, datetime.now().year))
        .group_by(PBResult.top_pb_code, Paper.year)
        .all()
    )
    return [
        {"pb_code": pb_code, "year": int(year), "value": int(count)}
        for pb_code, year, count in rows
    ]


def pb_year_matrix(db: Session) -> dict:
    """Matriz PB × año en formato listo para heatmap."""
    rows = pb_temporal_evolution(db)
    pbs = sorted({row["pb_code"] for row in rows})
    years = sorted({row["year"] for row in rows})
    matrix = {(row["pb_code"], row["year"]): row["value"] for row in rows}
    cells: list[dict] = []
    for pb in pbs:
        for year in years:
            cells.append({"pb_code": pb, "year": year, "value": matrix.get((pb, year), 0)})
    return {"pbs": pbs, "years": years, "cells": cells}


_TERM_SPLIT = re.compile(r"[;,|]")


def _parse_paper_terms(raw: str | None) -> list[str]:
    if not raw:
        return []
    items = [tok.strip().lower() for tok in _TERM_SPLIT.split(raw) if tok and tok.strip()]
    return list(dict.fromkeys(items))


def _paper_top_terms(doc_id: str | None) -> list[str]:
    """Términos más repetidos del paper (precalculados, sin stopwords).

    Lee la columna `top_terms_no_stopwords` del CSV maestro vía corpus_loader.
    Si la fila no existe o está vacía, devuelve [].
    """
    if not doc_id:
        return []
    from app.services.corpus_loader.service import load_bundle

    enriched = load_bundle().enriched
    if enriched.empty or "top_terms_no_stopwords" not in enriched.columns:
        return []
    rows = enriched.loc[enriched["doc_id"].astype(str) == str(doc_id), "top_terms_no_stopwords"]
    if rows.empty:
        return []
    return _parse_paper_terms(str(rows.iloc[0]))


def paper_comparison(db: Session, paper_id: uuid.UUID) -> dict | None:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return None

    pb_result = (
        db.query(PBResult)
        .filter(PBResult.paper_id == paper.id)
        .order_by(PBResult.created_at.desc())
        .first()
    )
    top_pb = pb_result.top_pb_code if pb_result else "PB-UNK"

    paper_length = len(paper.abstract_norm or "")
    global_avg_length = _papers_base_query(db).with_entities(func.avg(func.length(Paper.abstract_norm))).scalar() or 0.0

    pb_avg_length = (
        _papers_base_query(db)
        .join(PBResult, PBResult.paper_id == Paper.id)
        .filter(PBResult.top_pb_code == top_pb)
        .with_entities(func.avg(func.length(Paper.abstract_norm)))
        .scalar()
        or 0.0
    )

    paper_keywords = _parse_keywords(paper.keywords)
    global_top = top_keywords_global(db, limit=15)
    pb_top = top_keywords_by_pb(db, top_pb, limit=15)

    global_lookup = {item["keyword"]: item["value"] for item in global_top}
    pb_lookup = {item["keyword"]: item["value"] for item in pb_top}

    global_overlap = [
        {"keyword": keyword, "value": global_lookup[keyword]}
        for keyword in paper_keywords
        if keyword in global_lookup
    ]
    pb_overlap = [
        {"keyword": keyword, "value": pb_lookup[keyword]}
        for keyword in paper_keywords
        if keyword in pb_lookup
    ]

    # Términos más repetidos del paper (precalculados sin stopwords) y
    # cuáles de ellos coinciden con keywords frecuentes del PB.
    paper_terms = _paper_top_terms(paper.doc_id)
    pb_terms_overlap = [
        {"keyword": term, "value": pb_lookup[term]}
        for term in paper_terms
        if term in pb_lookup
    ]

    return {
        "paper_id": str(paper.id),
        "title": paper.title,
        "top_pb_code": top_pb,
        "length_comparison": {
            "paper_length": int(paper_length),
            "global_avg_length": float(global_avg_length),
            "pb_avg_length": float(pb_avg_length),
        },
        "keyword_comparison": {
            "paper_keywords": paper_keywords,
            "paper_terms": paper_terms,
            "global_overlap": global_overlap,
            "pb_overlap": pb_overlap,
            "pb_terms_overlap": pb_terms_overlap,
            "global_top_keywords": global_top,
            "pb_top_keywords": pb_top,
        },
    }
