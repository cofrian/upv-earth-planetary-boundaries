"""KPIs y distribuciones del corpus UPV alineadas con el plan de entrega.

Combina datos de la trazabilidad (corpus bruto / drops) con el corpus
enriquecido (corpus válido) y deja explícito el filtro metodológico
`abstract_char_len > 500` para diferenciar el subconjunto apto para
embeddings SPECTER2.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from functools import lru_cache
from typing import Any

import pandas as pd

from app.services.corpus_loader.precomputed import file_path
from app.services.corpus_loader.service import get_corpus_layers, load_bundle

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_eda_cache() -> dict | None:
    target = file_path("eda.json")
    if not target:
        return None
    try:
        with target.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        logger.info("EDA cache cargado desde %s", target)
        return payload
    except Exception as exc:  # noqa: BLE001
        logger.warning("EDA cache no se pudo cargar: %s", exc)
        return None


def reset_eda_cache() -> None:
    _load_eda_cache.cache_clear()


def cache_status() -> dict:
    return {
        "eda_cached": _load_eda_cache() is not None,
        "eda_path": str(file_path("eda.json")) if file_path("eda.json") else None,
    }


def _safe_int(series: pd.Series) -> int:
    if series is None or series.empty:
        return 0
    return int(series.shape[0])


def _drop_reason_breakdown(trace: pd.DataFrame) -> list[dict[str, Any]]:
    if trace.empty or "filter_reason_norm" not in trace.columns:
        return []
    dropped = trace[trace["filter_status_norm"] == "dropped"]
    counter: Counter[str] = Counter()
    for raw in dropped["filter_reason_norm"]:
        token = raw.strip()
        if not token:
            continue
        counter[token] += 1
    return [{"reason": reason, "count": count} for reason, count in counter.most_common()]


def _length_stats(values: pd.Series) -> dict[str, float]:
    if values.empty:
        return {"mean": 0.0, "median": 0.0, "p25": 0.0, "p75": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    desc = values.astype(float).describe(percentiles=[0.25, 0.5, 0.75, 0.9])
    return {
        "mean": float(desc.get("mean", 0.0)),
        "median": float(desc.get("50%", 0.0)),
        "p25": float(desc.get("25%", 0.0)),
        "p75": float(desc.get("75%", 0.0)),
        "p90": float(desc.get("90%", 0.0)),
        "min": float(desc.get("min", 0.0)),
        "max": float(desc.get("max", 0.0)),
    }


def _abstract_length_buckets(values: pd.Series) -> list[dict[str, Any]]:
    bins = [
        (0, 200, "0-200"),
        (200, 500, "200-500"),
        (500, 1000, "500-1000"),
        (1000, 1500, "1000-1500"),
        (1500, 2000, "1500-2000"),
        (2000, 3000, "2000-3000"),
        (3000, 5000, "3000-5000"),
        (5000, 1_000_000, "5000+"),
    ]
    out = []
    if values.empty:
        return [{"label": label, "value": 0} for _, _, label in bins]
    series = values.astype(float)
    for low, high, label in bins:
        count = int(((series >= low) & (series < high)).sum())
        out.append({"label": label, "value": count})
    return out


def _metadata_completeness(df: pd.DataFrame) -> list[dict[str, Any]]:
    fields = [
        ("DOI", "doi"),
        ("Journal", "journal"),
        ("Keywords", "keywords"),
        ("Authors", "authors"),
        ("Year", "year_int"),
        ("Language", "language"),
    ]
    if df.empty:
        return [{"field": label, "filled_pct": 0.0, "missing": 0, "filled": 0} for label, _ in fields]

    total = len(df)
    out: list[dict[str, Any]] = []
    for label, col in fields:
        if col not in df.columns:
            out.append({"field": label, "filled_pct": 0.0, "missing": total, "filled": 0})
            continue
        if df[col].dtype == object:
            filled = df[col].fillna("").astype(str).str.strip().ne("").sum()
        else:
            filled = df[col].notna().sum()
        filled = int(filled)
        out.append({
            "field": label,
            "filled_pct": round((filled / total) * 100.0, 2) if total else 0.0,
            "filled": filled,
            "missing": total - filled,
        })
    return out


def _papers_by_year(df: pd.DataFrame, max_year: int = 2024) -> list[dict[str, Any]]:
    if df.empty or "year_int" not in df.columns:
        return []
    valid_years = df.loc[df["year_int"].between(1900, max_year), "year_int"]
    if valid_years.empty:
        return []
    counts = valid_years.value_counts().sort_index()
    return [{"label": str(int(year)), "value": int(count)} for year, count in counts.items()]


_KEYWORD_SPLIT = re.compile(r"[,;|]")


def _keyword_counter(df: pd.DataFrame) -> Counter[str]:
    counter: Counter[str] = Counter()
    if df.empty or "keywords" not in df.columns:
        return counter
    for raw in df["keywords"].fillna(""):
        if not raw:
            continue
        for token in _KEYWORD_SPLIT.split(str(raw)):
            cleaned = token.strip().lower()
            if cleaned:
                counter[cleaned] += 1
    return counter


def _top_journals(df: pd.DataFrame, limit: int = 10) -> list[dict[str, Any]]:
    if df.empty or "journal" not in df.columns:
        return []
    journals = df["journal"].fillna("").astype(str).str.strip()
    journals = journals[journals.ne("")]
    if journals.empty:
        return []
    counts = journals.value_counts().head(limit)
    return [{"label": label, "value": int(count)} for label, count in counts.items()]


def _abstract_word_buckets(values: pd.Series) -> list[dict[str, Any]]:
    bins = [
        (0, 50, "<50"),
        (50, 100, "50-100"),
        (100, 200, "100-200"),
        (200, 300, "200-300"),
        (300, 400, "300-400"),
        (400, 600, "400-600"),
        (600, 100_000, "600+"),
    ]
    if values.empty:
        return [{"label": label, "value": 0} for _, _, label in bins]
    series = values.astype(float)
    return [
        {"label": label, "value": int(((series >= low) & (series < high)).sum())}
        for low, high, label in bins
    ]


def _from_cache(key: str) -> Any | None:
    cache = _load_eda_cache()
    if cache is None:
        return None
    return cache.get(key)


def corpus_summary() -> dict[str, Any]:
    cached = _from_cache("summary")
    if cached:
        return {
            "total_raw": cached["total_raw"],
            "with_abstract": cached["with_abstract"],
            "valid": cached["valid"],
            "for_embeddings": cached["for_embeddings"],
            "indexed": cached["indexed"],
            "valid_pct": cached["valid_pct"],
            "embedding_pct": cached["embedding_pct"],
            "embedding_pct_of_valid": cached["embedding_pct_of_valid"],
        }
    layers = get_corpus_layers()
    bundle = load_bundle()

    raw = layers["raw"]
    valid = layers["valid"]
    for_embeddings = layers["for_embeddings"]

    if not bundle.traceability.empty:
        total_raw = len(bundle.traceability)
        with_abstract = int(((bundle.traceability.get("filter_reason_norm", pd.Series(dtype=str))
                              .str.contains("abstract_empty") == False)  # noqa: E712
                             ).sum())
    else:
        total_raw = len(raw)
        with_abstract = int(bundle.enriched["has_abstract"].sum()) if not bundle.enriched.empty else 0

    return {
        "total_raw": int(total_raw),
        "with_abstract": int(with_abstract),
        "valid": int(len(valid)),
        "for_embeddings": int(len(for_embeddings)),
        "indexed": int(len(for_embeddings)),
        "valid_pct": round(len(valid) / total_raw * 100, 2) if total_raw else 0.0,
        "embedding_pct": round(len(for_embeddings) / total_raw * 100, 2) if total_raw else 0.0,
        "embedding_pct_of_valid": round(len(for_embeddings) / len(valid) * 100, 2) if len(valid) else 0.0,
    }


def abstract_length_distribution() -> dict[str, Any]:
    cached = _from_cache("abstract_lengths")
    if cached:
        return cached
    valid = get_corpus_layers()["valid"]
    if valid.empty:
        return {"items": [], "stats": _length_stats(pd.Series([], dtype=float))}

    values = valid["abstract_char_len"]
    return {
        "items": _abstract_length_buckets(values),
        "stats": _length_stats(values),
    }


def papers_by_year_distribution() -> list[dict[str, Any]]:
    cached = _from_cache("papers_by_year")
    if cached is not None:
        return cached
    return _papers_by_year(get_corpus_layers()["valid"])


def papers_by_year_for_embeddings_distribution() -> list[dict[str, Any]]:
    cached = _from_cache("papers_by_year_embeddings")
    if cached is not None:
        return cached
    return _papers_by_year(get_corpus_layers()["for_embeddings"])


def metadata_completeness() -> list[dict[str, Any]]:
    cached = _from_cache("metadata_completeness")
    if cached is not None:
        return cached
    return _metadata_completeness(get_corpus_layers()["valid"])


def top_keywords_corpus(limit: int = 20) -> list[dict[str, Any]]:
    cached = _from_cache("top_keywords")
    if cached:
        return cached[:limit]
    counts = _keyword_counter(get_corpus_layers()["valid"])
    return [{"keyword": kw, "value": value} for kw, value in counts.most_common(limit)]


def top_journals(limit: int = 10) -> list[dict[str, Any]]:
    cached = _from_cache("top_journals")
    if cached:
        return cached[:limit]
    return _top_journals(get_corpus_layers()["valid"], limit=limit)


def drop_reasons() -> list[dict[str, Any]]:
    cached = _from_cache("drop_reasons")
    if cached is not None:
        return cached
    return _drop_reason_breakdown(load_bundle().traceability)


def embedding_coverage() -> dict[str, Any]:
    cached = _from_cache("embedding_coverage")
    if cached:
        return cached
    layers = get_corpus_layers()
    valid = layers["valid"]
    for_embeddings = layers["for_embeddings"]

    embedding_lengths = for_embeddings["embedding_char_len"] if not for_embeddings.empty else pd.Series([], dtype=float)
    abstract_lengths = for_embeddings["abstract_char_len"] if not for_embeddings.empty else pd.Series([], dtype=float)

    return {
        "valid_total": int(len(valid)),
        "embedding_total": int(len(for_embeddings)),
        "discarded_short_abstract": int(((valid["abstract_char_len"] <= 500).sum()) if not valid.empty else 0),
        "embedding_text_length_stats": _length_stats(embedding_lengths),
        "abstract_length_stats": _length_stats(abstract_lengths),
        "approx_token_buckets": _abstract_word_buckets((embedding_lengths / 4).round()) if not embedding_lengths.empty else [],
        "indexed_total": int(len(for_embeddings)),
        "coverage_vs_valid_pct": round(len(for_embeddings) / len(valid) * 100, 2) if len(valid) else 0.0,
        "filter_rule": "abstract_char_len > 500",
        "embedding_text_rule": "title + clean_abstract_semantic",
    }


def top_unigrams(limit: int = 20) -> list[dict[str, Any]]:
    """Top unigrams del corpus calculados sobre los abstracts limpios.

    Lee `docs/eda/top_unigrams.csv` (precalculado por el EDA) y devuelve
    una lista de pares (término, frecuencia). A diferencia de
    `top_keywords_corpus`, esto refleja los términos más comunes en el
    texto de los papers, no las keywords declaradas por los autores.
    """
    cached = _from_cache("top_unigrams")
    if cached:
        return cached[:limit]

    from pathlib import Path

    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidate = base / "docs" / "eda" / "top_unigrams.csv"
        if candidate.exists():
            try:
                df = pd.read_csv(candidate)
                df.columns = [c.strip() for c in df.columns]
                if "term" in df.columns and "count" in df.columns:
                    return [
                        {"keyword": str(row["term"]), "value": int(row["count"])}
                        for _, row in df.head(limit).iterrows()
                    ]
            except Exception:  # noqa: BLE001
                pass
            break
    return []


def top_bigrams(limit: int = 20) -> list[dict[str, Any]]:
    """Bigramas precalculados en `docs/eda/top_bigrams.csv`.

    Si el archivo no está disponible, calcula al vuelo sobre `clean_abstract_lex`.
    """
    cached = _from_cache("top_bigrams")
    if cached:
        return cached[:limit]

    # Intento cargar desde docs/eda/top_bigrams.csv
    from pathlib import Path

    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidate = base / "docs" / "eda" / "top_bigrams.csv"
        if candidate.exists():
            try:
                df = pd.read_csv(candidate)
                df.columns = [c.strip() for c in df.columns]
                if "term" in df.columns and "count" in df.columns:
                    rows = [
                        {"keyword": str(row["term"]), "value": int(row["count"])}
                        for _, row in df.head(limit).iterrows()
                    ]
                    return rows
            except Exception:  # noqa: BLE001
                pass
            break

    # Fallback: calcular sobre clean_abstract_lex
    valid = get_corpus_layers()["valid"]
    if valid.empty or "clean_abstract_lex" not in valid.columns:
        return []
    counter: Counter[str] = Counter()
    for text in valid["clean_abstract_lex"].fillna(""):
        words = text.split()
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i + 1]}"
            counter[bg] += 1
    return [{"keyword": kw, "value": value} for kw, value in counter.most_common(limit)]


def words_per_abstract_distribution() -> list[dict[str, Any]]:
    """Distribución del número de palabras por abstract sobre el corpus válido."""
    cached = _from_cache("words_per_abstract")
    if cached is not None:
        return cached
    valid = get_corpus_layers()["valid"]
    if valid.empty or "abstract_norm" not in valid.columns:
        return []
    word_counts = valid["abstract_norm"].fillna("").astype(str).str.split().str.len()
    bins = [
        (0, 50, "<50"),
        (50, 100, "50-100"),
        (100, 150, "100-150"),
        (150, 200, "150-200"),
        (200, 300, "200-300"),
        (300, 400, "300-400"),
        (400, 600, "400-600"),
        (600, 100_000, "600+"),
    ]
    return [
        {"label": label, "value": int(((word_counts >= low) & (word_counts < high)).sum())}
        for low, high, label in bins
    ]


def temporal_quality_evolution() -> list[dict[str, Any]]:
    """Evolución temporal con conteos por capa (válido vs apto embeddings)."""
    cached = _from_cache("temporal_quality")
    if cached is not None:
        return cached
    layers = get_corpus_layers()
    valid = layers["valid"]
    for_emb = layers["for_embeddings"]
    if valid.empty:
        return []
    valid_counts = valid.loc[valid["year_int"].between(1900, 2024), "year_int"].value_counts().sort_index()
    emb_counts = for_emb.loc[for_emb["year_int"].between(1900, 2024), "year_int"].value_counts().sort_index() if not for_emb.empty else pd.Series(dtype=int)
    out = []
    for year, total in valid_counts.items():
        out.append({
            "year": int(year),
            "valid": int(total),
            "for_embeddings": int(emb_counts.get(year, 0)),
        })
    return out


def temporal_range() -> dict[str, Any]:
    valid = get_corpus_layers()["valid"]
    if valid.empty or "year_int" not in valid.columns:
        return {"min_year": None, "max_year": None}
    years = valid["year_int"].dropna()
    years = years[years.between(1900, 2024)]
    if years.empty:
        return {"min_year": None, "max_year": None}
    return {"min_year": int(years.min()), "max_year": int(years.max())}


def overview_kpis() -> dict[str, Any]:
    """Bloque de KPIs para Dashboard y AED.

    Devuelve métricas detalladas con la separación entre corpus bruto,
    con abstract, válido, apto para embeddings e indexado.
    """
    cached = _from_cache("summary")
    if cached:
        return cached

    summary = corpus_summary()
    layers = get_corpus_layers()
    valid = layers["valid"]

    abstract_stats = _length_stats(valid["abstract_char_len"]) if not valid.empty else {}

    if not valid.empty:
        unique_journals = int(valid["journal"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().nunique())
        with_doi = int(valid["doi"].fillna("").astype(str).str.strip().ne("").sum())
        with_keywords = int(valid["keywords"].fillna("").astype(str).str.strip().ne("").sum())
    else:
        unique_journals = with_doi = with_keywords = 0

    temporal = temporal_range()

    return {
        **summary,
        "avg_abstract_length": round(abstract_stats.get("mean", 0.0), 1),
        "median_abstract_length": round(abstract_stats.get("median", 0.0), 1),
        "p90_abstract_length": round(abstract_stats.get("p90", 0.0), 1),
        "unique_journals": unique_journals,
        "papers_with_doi": with_doi,
        "papers_with_keywords": with_keywords,
        "min_year": temporal["min_year"],
        "max_year": temporal["max_year"],
        "filter_rule": "abstract_char_len > 500",
        "embedding_text_rule": "title + clean_abstract_semantic",
    }
