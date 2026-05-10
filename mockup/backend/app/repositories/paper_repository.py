from __future__ import annotations

import uuid

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.db.models.paper import Paper
from app.db.models.pb_result import PBResult

HIDDEN_DOC_IDS = {"b39624d6c38a"}
HIDDEN_TITLE_PATTERNS = ("%chapter 34 the role of hydrological modelling uncertainties%",)


class PaperRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_papers(
        self,
        query: str | None,
        year: int | None,
        max_year: int | None,
        journal: str | None,
        pb: str | None,
        doi: str | None,
        keywords: str | None,
        sort: str,
        page: int,
        page_size: int,
        min_abstract_len: int | None = None,
    ) -> tuple[list[Paper], int]:
        source_norm = func.lower(func.trim(func.coalesce(Paper.source, "")))
        title_norm = func.lower(func.trim(func.coalesce(Paper.title, "")))
        q = self.db.query(Paper).filter(
            ~or_(
                source_norm == "uploaded_pdf",
                Paper.doc_id.like("upload-%"),
                Paper.doc_id.in_(HIDDEN_DOC_IDS),
                *[title_norm.like(pattern) for pattern in HIDDEN_TITLE_PATTERNS],
            )
        )

        if query:
            like_query = f"%{query.lower()}%"
            q = q.filter(func.lower(Paper.title).like(like_query) | func.lower(Paper.abstract_norm).like(like_query))
        if year:
            q = q.filter(Paper.year == year)
        if max_year:
            q = q.filter(Paper.year.is_(None) | (Paper.year <= max_year))
        if journal:
            q = q.filter(Paper.journal == journal)
        if doi:
            q = q.filter(Paper.doi == doi)
        if keywords:
            q = q.filter(func.lower(Paper.keywords).like(f"%{keywords.lower()}%"))
        if pb:
            q = q.join(PBResult, PBResult.paper_id == Paper.id).filter(PBResult.top_pb_code == pb)
        if min_abstract_len is not None and min_abstract_len > 0:
            q = q.filter(func.length(Paper.abstract_norm) >= min_abstract_len)

        total = q.count()

        if sort == "year_desc":
            q = q.order_by(desc(Paper.year))
        elif sort == "year_asc":
            q = q.order_by(Paper.year.asc())
        elif sort == "abstract_len_desc":
            q = q.order_by(desc(func.length(Paper.abstract_norm)))
        elif sort == "abstract_len_asc":
            q = q.order_by(func.length(Paper.abstract_norm).asc())
        elif sort == "title_asc":
            q = q.order_by(Paper.title.asc())
        else:
            q = q.order_by(desc(Paper.created_at))

        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_id(self, paper_id: uuid.UUID) -> Paper | None:
        return self.db.query(Paper).filter(Paper.id == paper_id).first()

    def get_latest_pb_result(self, paper_id: uuid.UUID) -> PBResult | None:
        return (
            self.db.query(PBResult)
            .filter(PBResult.paper_id == paper_id)
            .order_by(desc(PBResult.created_at))
            .first()
        )
