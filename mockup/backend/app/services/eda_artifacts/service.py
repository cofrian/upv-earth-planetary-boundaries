"""Carga los CSVs precalculados del EDA desde `docs/eda/`.

Estos artefactos los generó el equipo en notebooks fuera del backend
(EDA, similitud PB, TFIDF, topics semánticos). El backend los expone
como endpoints para que el frontend los muestre sin duplicar trabajo.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _eda_dir() -> Path | None:
    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidate = base / "docs" / "eda"
        if candidate.exists():
            return candidate
    return None


def eda_dir() -> Path | None:
    """Public accessor for the EDA directory (used by the API to serve assets)."""
    return _eda_dir()


def _normalize_pb_slug(pb_code: str) -> str:
    """Convierte '1 - Climate Change' → '1_climate_change'.

    El nombre de los archivos PNG generados por el EDA sigue ese patrón
    (snake_case en minúsculas, prefijo con el número del PB).
    """
    cleaned = pb_code.strip().lower()
    cleaned = cleaned.replace(" - ", " ").replace("-", " ")
    cleaned = "_".join(part for part in cleaned.split() if part)
    return cleaned


def wordcloud_image_path(pb_code: str) -> Path | None:
    base = _eda_dir()
    if not base:
        return None
    slug = _normalize_pb_slug(pb_code)
    if not slug:
        return None
    candidate = base / "wordcloud_por_pb" / f"{slug}_wordcloud.png"
    if candidate.exists():
        return candidate
    # Fallback: buscar prefijo numérico (p. ej. PB code = "1 - Climate Change"
    # → 1_climate_change pero el archivo podría llamarse 1_climate_change_wordcloud.png).
    parts = slug.split("_", 1)
    if parts:
        prefix = parts[0]
        directory = base / "wordcloud_por_pb"
        if directory.exists():
            for path in directory.glob(f"{prefix}_*_wordcloud.png"):
                return path
    return None


@lru_cache(maxsize=1)
def _df(filename: str) -> pd.DataFrame | None:
    base = _eda_dir()
    if not base:
        return None
    target = base / filename
    if not target.exists():
        return None
    try:
        return pd.read_csv(target)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer %s: %s", target, exc)
        return None


def reset_cache() -> None:
    _df.cache_clear()


# ----- PB similarity -----

SIMILARITY_FILES = {
    "embeddings": "similitud_pb_por_embeddings_semanticos.csv",
    "tfidf": "similitud_pb_por_terminos_tfidf.csv",
    "corpus": "similitud_pb_por_corpus_completo.csv",
}

SIMILARITY_PAIR_FILES = {
    "embeddings": "similitud_pb_por_embeddings_semanticos_top_pairs.csv",
    "tfidf": "similitud_pb_por_terminos_tfidf_top_pairs.csv",
    "corpus": "similitud_pb_por_corpus_completo_top_pairs.csv",
}


def pb_similarity_matrix(metric: str = "embeddings") -> dict | None:
    """Devuelve la matriz cuadrada PB × PB precalculada.

    Args:
        metric: una de "embeddings" (default), "tfidf", "corpus".
    """
    filename = SIMILARITY_FILES.get(metric)
    if not filename:
        return None
    df = _df(filename)
    if df is None or df.empty:
        return None
    df = df.copy()
    # La primera columna es el nombre del PB (etiqueta de fila)
    if df.columns[0] in ("Unnamed: 0", "pb_folder"):
        df = df.rename(columns={df.columns[0]: "pb"})
    else:
        df = df.rename(columns={df.columns[0]: "pb"})
    pbs = df["pb"].tolist()
    cells: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        row_pb = str(row["pb"])
        for col in df.columns:
            if col == "pb":
                continue
            try:
                value = float(row[col])
            except (TypeError, ValueError):
                continue
            cells.append({"pb_a": row_pb, "pb_b": str(col), "value": round(value, 4)})
    return {"metric": metric, "pbs": pbs, "cells": cells}


def pb_similarity_top_pairs(metric: str = "embeddings", limit: int = 10) -> list[dict]:
    filename = SIMILARITY_PAIR_FILES.get(metric)
    if not filename:
        return []
    df = _df(filename)
    if df is None or df.empty:
        return []
    df = df.head(limit)
    return [
        {
            "pb_a": str(row.get("pb_a", "")),
            "pb_b": str(row.get("pb_b", "")),
            "similarity": round(float(row.get("similarity", 0.0)), 4),
        }
        for _, row in df.iterrows()
    ]


# ----- Abstract complexity by PB -----


def abstract_complexity_by_pb() -> list[dict]:
    df = _df("complejidad_abstract_por_pb_summary.csv")
    if df is None or df.empty:
        return []
    out = []
    for _, row in df.iterrows():
        out.append({
            "pb_code": str(row["pb_folder"]),
            "count": int(row.get("count", 0) or 0),
            "mean": float(row.get("mean", 0.0) or 0.0),
            "median": float(row.get("median", 0.0) or 0.0),
            "std": float(row.get("std", 0.0) or 0.0),
            "min": float(row.get("min", 0.0) or 0.0),
            "max": float(row.get("max", 0.0) or 0.0),
        })
    return out


# ----- TFIDF top terms by PB -----


def tfidf_terms_by_pb(pb_code: str | None = None, limit: int = 10) -> list[dict]:
    """Devuelve top términos TF-IDF por PB (todos o filtrado por uno)."""
    df = _df("tfidf_top_terms_por_pb.csv")
    if df is None or df.empty:
        return []
    if pb_code:
        df = df[df["pb_folder"] == pb_code]
    out: list[dict] = []
    grouped = df.groupby("pb_folder", sort=False)
    for pb, group in grouped:
        sub = group.sort_values("tfidf_mean", ascending=False).head(limit)
        for _, row in sub.iterrows():
            out.append({
                "pb_code": str(pb),
                "term": str(row["term"]),
                "value": round(float(row["tfidf_mean"]), 6),
            })
    return out


# ----- Wordcloud doc-frequency terms by PB -----


def wordcloud_terms_by_pb(pb_code: str | None = None, limit: int = 20) -> list[dict]:
    df = _df("wordcloud_por_pb_top_terms.csv")
    if df is None or df.empty:
        return []
    if pb_code:
        df = df[df["pb_folder"] == pb_code]
    out: list[dict] = []
    grouped = df.groupby("pb_folder", sort=False)
    for pb, group in grouped:
        sub = group.head(limit)
        for _, row in sub.iterrows():
            out.append({
                "pb_code": str(pb),
                "term": str(row["term"]),
                "value": int(row.get("doc_frequency", 0) or 0),
            })
    return out


# ----- Semantic topic clusters -----


def semantic_topic_summary() -> list[dict]:
    df = _df("semantic_topic_cluster_summary.csv")
    if df is None or df.empty:
        return []
    return [
        {
            "cluster_id": int(row["cluster_id"]),
            "label": str(row.get("tema_auto", "")),
            "n_docs": int(row.get("n_docs", 0) or 0),
            "pct_docs": float(row.get("pct_docs", 0.0) or 0.0),
        }
        for _, row in df.iterrows()
    ]


# ----- PB doc counts (canonical from EDA) -----


def pb_doc_counts() -> list[dict]:
    df = _df("pb_doc_counts.csv")
    if df is None or df.empty:
        return []
    return [
        {"pb_code": str(row["pb_folder"]), "n_docs": int(row["n_docs"])}
        for _, row in df.iterrows()
    ]
