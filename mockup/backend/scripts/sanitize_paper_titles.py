"""Sanea los títulos y años de los papers en BD.

Pipeline en tres pasadas:

1. Aplica `sanitize_title` (regex local) sobre cada título contaminado.
2. Para los títulos que quedan vacíos tras la limpieza, intenta
   reinferir uno legible llamando a Ollama (Qwen) sobre el abstract.
3. Para los papers con año inválido (>YEAR_MAX, <YEAR_MIN o NULL),
   intenta inferir el año real llamando a Ollama con título + abstract
   + DOI si existe.

El script imprime un resumen y NO toca papers cuyo título / año ya
parecen correctos.

Ejecución:
    python -m scripts.sanitize_paper_titles [--dry-run] [--llm-limit 200]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import urllib.error
import urllib.request

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.paper import Paper
from app.db.session import SessionLocal
from app.services.text_cleaning.sanitizers import (
    looks_like_dirty_title,
    sanitize_semantic_text,
    sanitize_title,
)

YEAR_MIN = 1900
YEAR_MAX = 2026
_DOI_YEAR_RE = re.compile(r"(?:^|[/\-_.])((?:19|20)\d{2})(?:[/\-_.]|$)")
_BARE_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

logger = logging.getLogger("sanitize_titles")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


PROMPT_TITLE = (
    "You are an academic editor. Below is the abstract of a scientific paper. "
    "Infer a concise, descriptive English title (max 25 words). Output ONLY the title text, "
    "no quotes, no markdown, no preface.\n\n"
    "Abstract:\n{abstract}\n\nTitle:"
)

PROMPT_YEAR = (
    "You are a bibliographic assistant. Given the metadata below, identify the most likely "
    "year of publication of the paper. Return ONLY a 4-digit year between {ymin} and {ymax}. "
    "If you cannot determine it, return UNKNOWN.\n\n"
    "DOI: {doi}\n"
    "Title: {title}\n"
    "Abstract: {abstract}\n\n"
    "Year:"
)


def _ollama_call(prompt: str, num_predict: int, timeout: int = 30) -> str | None:
    payload = {
        "model": settings.ollama_model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        settings.ollama_url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Ollama no respondió: %s", exc)
        return None
    return (body.get("response") or "").strip()


def _ollama_infer_title(abstract: str) -> str | None:
    if not abstract:
        return None
    raw = _ollama_call(PROMPT_TITLE.format(abstract=abstract[:1800]), num_predict=80)
    if not raw:
        return None
    text = raw.strip().strip('"').strip("'")
    text = text.split("\n", 1)[0].strip()
    if len(text) < 12 or looks_like_dirty_title(text):
        return None
    return text


def _year_from_doi(doi: str | None) -> int | None:
    if not doi:
        return None
    match = _DOI_YEAR_RE.search(doi)
    if not match:
        return None
    candidate = int(match.group(1))
    if YEAR_MIN <= candidate <= YEAR_MAX:
        return candidate
    return None


def _ollama_infer_year(title: str, abstract: str, doi: str | None) -> int | None:
    if not (title or abstract):
        return None
    prompt = PROMPT_YEAR.format(
        doi=doi or "(none)",
        title=(title or "")[:240],
        abstract=(abstract or "")[:1500],
        ymin=YEAR_MIN,
        ymax=YEAR_MAX,
    )
    raw = _ollama_call(prompt, num_predict=8)
    if not raw:
        return None
    match = _BARE_YEAR_RE.search(raw)
    if not match:
        return None
    candidate = int(match.group(1))
    if YEAR_MIN <= candidate <= YEAR_MAX:
        return candidate
    return None


def _process_titles(db: Session, dry_run: bool, llm_limit: int) -> tuple[dict, int]:
    stats = {
        "scanned": 0,
        "regex_cleaned": 0,
        "llm_recovered": 0,
        "llm_failed": 0,
        "kept_unchanged": 0,
    }
    llm_calls = 0

    for paper in db.query(Paper).all():
        stats["scanned"] += 1
        original = (paper.title or "").strip()
        if not looks_like_dirty_title(original):
            stats["kept_unchanged"] += 1
            continue

        cleaned = sanitize_title(original)
        if cleaned and not looks_like_dirty_title(cleaned):
            if not dry_run:
                paper.title = cleaned
            stats["regex_cleaned"] += 1
            logger.debug("regex %s: %r -> %r", paper.doc_id, original[:60], cleaned[:60])
            continue

        if llm_calls >= llm_limit:
            stats["kept_unchanged"] += 1
            continue
        llm_calls += 1
        abstract_clean = sanitize_semantic_text(paper.abstract_norm or paper.abstract_raw or "")
        inferred = _ollama_infer_title(abstract_clean)
        if inferred:
            if not dry_run:
                paper.title = inferred
            stats["llm_recovered"] += 1
            logger.info("title-LLM %s: -> %s", paper.doc_id, inferred[:120])
        else:
            stats["llm_failed"] += 1

    return stats, llm_calls


def _process_years(
    db: Session, dry_run: bool, llm_limit: int, llm_used: int
) -> dict:
    stats = {
        "scanned": 0,
        "doi_recovered": 0,
        "llm_recovered": 0,
        "llm_failed": 0,
        "kept_unchanged": 0,
    }
    bad = (
        db.query(Paper)
        .filter((Paper.year > YEAR_MAX) | (Paper.year < YEAR_MIN) | (Paper.year.is_(None)))
        .all()
    )
    stats["scanned"] = len(bad)

    for paper in bad:
        # 1) Intento barato: año embebido en el DOI.
        from_doi = _year_from_doi(paper.doi)
        if from_doi:
            if not dry_run:
                paper.year = from_doi
            stats["doi_recovered"] += 1
            logger.info("year-DOI %s: %s -> %s", paper.doc_id, paper.year, from_doi)
            continue

        # 2) Recovery vía LLM si nos queda crédito.
        if llm_used >= llm_limit:
            stats["kept_unchanged"] += 1
            continue
        llm_used += 1
        abstract_clean = sanitize_semantic_text(paper.abstract_norm or paper.abstract_raw or "")
        inferred = _ollama_infer_year(paper.title or "", abstract_clean, paper.doi)
        if inferred:
            if not dry_run:
                paper.year = inferred
            stats["llm_recovered"] += 1
            logger.info("year-LLM %s: %s -> %s", paper.doc_id, paper.year, inferred)
        else:
            stats["llm_failed"] += 1

    return stats


def _process(db: Session, dry_run: bool, llm_limit: int) -> tuple[dict, dict]:
    title_stats, llm_used = _process_titles(db, dry_run, llm_limit)
    year_stats = _process_years(db, dry_run, llm_limit, llm_used)
    if not dry_run:
        db.commit()
    return title_stats, year_stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No escribe en BD")
    parser.add_argument(
        "--llm-limit",
        type=int,
        default=200,
        help="Máximo de llamadas a Ollama (las regex no cuentan)",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        title_stats, year_stats = _process(db, dry_run=args.dry_run, llm_limit=args.llm_limit)

    print("Títulos:")
    for key, value in title_stats.items():
        print(f"  {key:20s}: {value}")
    print("Años:")
    for key, value in year_stats.items():
        print(f"  {key:20s}: {value}")
    if args.dry_run:
        print("(dry-run · BD intacta)")


if __name__ == "__main__":
    main()
