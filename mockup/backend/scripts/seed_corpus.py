import csv
import os
import uuid

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.paper import Paper
from app.db.models.pb_result import PBResult
from app.db.session import SessionLocal, engine

csv.field_size_limit(10**8)

CLEAN_PATH = os.getenv(
    "SEED_CLEAN_PATH",
    "/app/data/corpus/master_corpus_mixto_clean_enriched.csv",
)
TRACE_PATH = os.getenv(
    "SEED_TRACE_PATH",
    "/app/data/corpus/master_corpus_mixto_traceability.csv",
)


def _parse_year(value: str | None) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        year = int(float(raw))
    except ValueError:
        return None
    if 1900 <= year <= 2100:
        return year
    return None


def seed_papers(db: Session) -> dict[str, uuid.UUID]:
    paper_ids: dict[str, uuid.UUID] = {}
    with open(CLEAN_PATH, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            doc_id = row.get("doc_id") or f"seed-{uuid.uuid4()}"
            paper = Paper(
                doc_id=doc_id,
                title=row.get("title", ""),
                abstract_raw=row.get("abstract_raw", row.get("abstract", "")),
                abstract_norm=row.get("abstract_norm", row.get("abstract", "")),
                clean_abstract=row.get("clean_abstract_lex", row.get("clean_abstract", "")),
                year=_parse_year(row.get("year")),
                doi=row.get("doi"),
                source=row.get("source"),
                authors=row.get("authors"),
                keywords=row.get("keywords"),
                journal=row.get("journal"),
                language=row.get("language"),
                pdf_path=None,
            )
            db.add(paper)
            db.flush()
            paper_ids[doc_id] = paper.id
    db.commit()
    return paper_ids


def seed_pb_from_trace(db: Session, paper_ids: dict[str, uuid.UUID]) -> None:
    with open(TRACE_PATH, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("filter_status") != "kept":
                continue
            doc_id = row.get("doc_id")
            paper_id = paper_ids.get(doc_id or "")
            if not paper_id:
                continue

            pb_code = row.get("pb_folder") or "PB-UNK"
            result = PBResult(
                paper_id=paper_id,
                model_version="seed-traceability-v1",
                top_pb_code=pb_code,
                top_pb_score=0.65,
                secondary_pbs={},
                score_map={pb_code: 0.65},
                threshold_used=0.3,
                explanation_text="Resultado inicial cargado desde trazabilidad histórica del corpus.",
            )
            db.add(result)
    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding papers...")
        paper_ids = seed_papers(db)
        print("Seeding PB results from traceability...")
        seed_pb_from_trace(db, paper_ids)
        print("Seed completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
