"""Recupera AED del corpus para inyectar como contexto al chatbot.

NO calcula nada nuevo: reutiliza los servicios `corpus_quality`,
`analytics_service` y `similarity_search.index_status`. Si esos servicios
fallan o están vacíos, devuelve un dict mínimo para que el LLM pueda decir
"no tengo ese dato".
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _safe(call, default):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.debug("analytics_retriever fallback: %s", exc)
        return default


def fetch_corpus_snapshot(db: Session) -> dict[str, Any]:
    """Resumen ejecutivo del corpus alineado con el dashboard."""
    from app.services.corpus_quality.service import (
        embedding_coverage,
        overview_kpis,
        papers_by_year_distribution,
    )
    from app.services.analytics_service.service import distribution_by_pb
    from app.services.similarity_search.service import index_status

    kpis = _safe(overview_kpis, {})
    coverage = _safe(embedding_coverage, {})
    by_year = _safe(papers_by_year_distribution, [])
    by_pb = _safe(lambda: distribution_by_pb(db), [])
    idx = _safe(index_status, {})

    return {
        "kpis": {
            "total_raw": kpis.get("total_raw"),
            "with_abstract": kpis.get("with_abstract"),
            "valid": kpis.get("valid"),
            "for_embeddings": kpis.get("for_embeddings"),
            "indexed": kpis.get("indexed"),
            "valid_pct": kpis.get("valid_pct"),
            "embedding_pct_of_valid": kpis.get("embedding_pct_of_valid"),
            "avg_abstract_length": kpis.get("avg_abstract_length"),
            "median_abstract_length": kpis.get("median_abstract_length"),
            "min_year": kpis.get("min_year"),
            "max_year": kpis.get("max_year"),
            "filter_rule": kpis.get("filter_rule") or "abstract_char_len > 500",
            "embedding_text_rule": kpis.get("embedding_text_rule") or "title + clean_abstract_semantic",
        },
        "embedding_coverage": {
            "valid_total": coverage.get("valid_total"),
            "embedding_total": coverage.get("embedding_total"),
            "discarded_short_abstract": coverage.get("discarded_short_abstract"),
            "indexed_total": coverage.get("indexed_total"),
            "coverage_vs_valid_pct": coverage.get("coverage_vs_valid_pct"),
        },
        "year_distribution": list(by_year)[:80],
        "pb_distribution": list(by_pb),
        "index": {
            "model_id": idx.get("model_id"),
            "embedding_dim": idx.get("embedding_dim"),
            "vectors": idx.get("vectors"),
            "is_specter": idx.get("is_specter"),
            "fallback_used": idx.get("fallback_used"),
            "is_precomputed": idx.get("is_precomputed"),
            "source": idx.get("source"),
        },
    }
