"""Carga unificada del corpus UPV.

Mantiene en memoria los DataFrames principales (`enriched`, `traceability`)
y expone vistas derivadas para el resto de servicios analíticos.

La separación canónica (consistente con el plan de entrega) es:

* `raw`            -> todo el corpus procesado (traceability completo).
* `with_abstract`  -> filas con `abstract_norm` no vacío.
* `valid`          -> filas marcadas como `kept` en la trazabilidad
                      (lenguaje y reglas básicas superadas).
* `for_embeddings` -> `abstract_char_len > 500` sobre el corpus válido.
* `indexed`        -> subconjunto presente en el índice FAISS.

Las columnas y rutas siguen la convención documentada en `docs/`.
"""
from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)


def _repo_data_corpus(filename: str) -> str:
    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            candidate = here.parents[parents_up] / "data" / "corpus" / filename
        except IndexError:
            continue
        if candidate.exists():
            return str(candidate)
    return ""


_DEFAULT_ENRICHED_CANDIDATES = [
    "/app/data/corpus/master_corpus_mixto_clean_enriched.csv",
    _repo_data_corpus("master_corpus_mixto_clean_enriched.csv"),
    "/app/data/corpus/master_corpus_mixto_1000_clean_enriched.csv",
    _repo_data_corpus("master_corpus_mixto_1000_clean_enriched.csv"),
]
_DEFAULT_TRACE_CANDIDATES = [
    "/app/data/corpus/master_corpus_mixto_traceability.csv",
    _repo_data_corpus("master_corpus_mixto_traceability.csv"),
    "/app/data/corpus/master_corpus_mixto_1000_traceability.csv",
    _repo_data_corpus("master_corpus_mixto_1000_traceability.csv"),
]


def _resolve_path(env_key: str, fallbacks: Iterable[str]) -> str | None:
    candidate = os.getenv(env_key)
    if candidate and Path(candidate).exists():
        return candidate
    for path in fallbacks:
        if path and Path(path).exists():
            return path
    return None


def get_enriched_path() -> str | None:
    return _resolve_path("CORPUS_ENRICHED_CSV", _DEFAULT_ENRICHED_CANDIDATES)


def get_traceability_path() -> str | None:
    return _resolve_path("CORPUS_TRACEABILITY_CSV", _DEFAULT_TRACE_CANDIDATES)


@dataclass
class CorpusBundle:
    enriched: pd.DataFrame
    traceability: pd.DataFrame
    enriched_path: str | None
    traceability_path: str | None


@lru_cache(maxsize=1)
def load_bundle() -> CorpusBundle:
    """Lee los CSVs maestros una sola vez y deja DataFrames listos para análisis.

    No falla si alguno no existe: devuelve DataFrames vacíos para que las
    rutinas dependientes degraden con elegancia.
    """
    enriched_path = get_enriched_path()
    trace_path = get_traceability_path()
    csv.field_size_limit(10**7)

    if enriched_path:
        enriched = pd.read_csv(enriched_path, dtype=str).fillna("")
        enriched = _normalize_enriched(enriched)
    else:
        logger.warning("master_corpus_mixto_clean_enriched.csv no encontrado")
        enriched = pd.DataFrame()

    if trace_path:
        # El trace puede llevar columnas pesadas (full_text ~3 GB). Solo
        # cargamos lo que necesitan los servicios de auditoría/calidad.
        trace_usecols = [
            "doc_id",
            "year",
            "source",
            "filter_status",
            "filter_reason",
            "pb_folder",
            "language",
            "abstract_length",
        ]
        try:
            trace = pd.read_csv(
                trace_path,
                dtype=str,
                usecols=lambda c: c in trace_usecols,
            ).fillna("")
        except ValueError:
            trace = pd.read_csv(trace_path, dtype=str).fillna("")
        trace = _normalize_trace(trace)
    else:
        logger.warning("master_corpus_mixto_traceability.csv no encontrado")
        trace = pd.DataFrame()

    return CorpusBundle(
        enriched=enriched,
        traceability=trace,
        enriched_path=enriched_path,
        traceability_path=trace_path,
    )


def reset_cache() -> None:
    """Permite invalidar el cache (test/debug)."""
    load_bundle.cache_clear()


def _coerce_year(value: object) -> int | None:
    if value is None:
        return None
    try:
        year = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    # Tope superior conservador: el corpus mixto trae mucho ruido tipográfico
    # (años "2050", "2099" extraídos de columnas, números de página, etc.).
    if 1900 <= year <= 2026:
        return year
    return None


def _normalize_enriched(df: pd.DataFrame) -> pd.DataFrame:
    from app.services.text_cleaning.sanitizers import sanitize_semantic_text, sanitize_title

    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # Asegurar columnas clave aunque vengan vacías.
    for col in ["title", "abstract_norm", "abstract", "clean_abstract", "clean_abstract_lex",
                "doi", "journal", "keywords", "source", "language", "year", "doc_id",
                "top_terms_no_stopwords"]:
        if col not in df.columns:
            df[col] = ""

    df["year_int"] = df["year"].map(_coerce_year)
    df["abstract_norm"] = df["abstract_norm"].astype(str)
    df["abstract"] = df["abstract"].astype(str)
    df["clean_abstract_lex"] = df.get("clean_abstract_lex", df.get("clean_abstract", "")).astype(str)

    # Limpieza semántica real: elimina URLs, DOIs, copyright, license,
    # cabeceras de journal y citaciones numéricas antes del embedding.
    raw_semantic = df["abstract_norm"].where(df["abstract_norm"].str.len() > 0, df["abstract"])
    df["clean_abstract_semantic"] = raw_semantic.fillna("").map(sanitize_semantic_text)

    # Título saneado: si queda vacío tras limpiar (cabecera bibliográfica
    # imposible de salvar) NO usamos el original sucio para el embedding —
    # el SPECTER se queda solo con el abstract limpio. Para la UI seguimos
    # mostrando el original sucio mediante df["title"] (sin tocar).
    cleaned_titles = df["title"].fillna("").map(sanitize_title)
    df["title_clean"] = cleaned_titles.where(cleaned_titles.str.len() >= 12, "")

    df["embedding_text"] = (
        df["title_clean"].fillna("") + " " + df["clean_abstract_semantic"].fillna("")
    ).str.strip()

    df["abstract_char_len"] = df["abstract_norm"].str.len()
    df["title_char_len"] = df["title_clean"].str.len()
    df["embedding_char_len"] = df["embedding_text"].str.len()
    df["has_abstract"] = df["abstract_norm"].str.len() > 0
    df["is_valid_for_embedding"] = df["abstract_char_len"] > 500
    return df


def _normalize_trace(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    if "year" in df.columns:
        df["year_int"] = df["year"].map(_coerce_year)
    if "filter_status" in df.columns:
        df["filter_status_norm"] = df["filter_status"].astype(str).str.strip().str.lower()
    else:
        df["filter_status_norm"] = ""
    if "filter_reason" in df.columns:
        df["filter_reason_norm"] = df["filter_reason"].astype(str).str.strip()
    else:
        df["filter_reason_norm"] = ""
    return df


def get_corpus_layers() -> dict[str, pd.DataFrame]:
    """Devuelve las capas del corpus alineadas con el plan de producto."""
    bundle = load_bundle()
    enriched = bundle.enriched
    trace = bundle.traceability

    raw = trace if not trace.empty else enriched

    if not trace.empty and "filter_reason_norm" in trace.columns:
        with_abstract = trace[~trace["filter_reason_norm"].str.contains("abstract_empty", na=False)]
    elif not enriched.empty and "has_abstract" in enriched.columns:
        with_abstract = enriched[enriched["has_abstract"]]
    else:
        with_abstract = enriched

    if not trace.empty and "filter_status_norm" in trace.columns and not enriched.empty:
        valid_doc_ids = set(trace.loc[trace["filter_status_norm"] == "kept", "doc_id"].astype(str))
        valid = enriched[enriched["doc_id"].astype(str).isin(valid_doc_ids)]
    elif not enriched.empty and "has_abstract" in enriched.columns:
        valid = enriched[enriched["has_abstract"]]
    else:
        valid = enriched

    if not valid.empty and "is_valid_for_embedding" in valid.columns:
        for_embeddings = valid[valid["is_valid_for_embedding"]]
    else:
        for_embeddings = valid

    return {
        "raw": raw,
        "with_abstract": with_abstract,
        "valid": valid,
        "for_embeddings": for_embeddings,
    }
