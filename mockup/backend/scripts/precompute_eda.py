"""Precalcula los KPIs y distribuciones del EDA.

Genera un único JSON con todo lo que el dashboard y la página `/analysis`
necesitan. Se carga al arranque del backend (lazy) para que las páginas
respondan en milisegundos.

Ejecución:
    python -m scripts.precompute_eda
"""
from __future__ import annotations

import json

from app.services.corpus_loader.precomputed import writable_file
from app.services.corpus_quality.service import (
    abstract_length_distribution,
    drop_reasons,
    embedding_coverage,
    metadata_completeness,
    overview_kpis,
    papers_by_year_distribution,
    papers_by_year_for_embeddings_distribution,
    temporal_quality_evolution,
    top_journals,
    top_keywords_corpus,
)


def build_payload() -> dict:
    return {
        "summary": overview_kpis(),
        "abstract_lengths": abstract_length_distribution(),
        "papers_by_year": papers_by_year_distribution(),
        "papers_by_year_embeddings": papers_by_year_for_embeddings_distribution(),
        "metadata_completeness": metadata_completeness(),
        "drop_reasons": drop_reasons(),
        "embedding_coverage": embedding_coverage(),
        "temporal_quality": temporal_quality_evolution(),
        "top_keywords": top_keywords_corpus(limit=30),
        "top_journals": top_journals(limit=15),
    }


def main() -> None:
    payload = build_payload()
    target = writable_file("eda.json")
    with target.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"EDA precalculado guardado en {target}")
    print(f"Resumen: {payload['summary']}")


if __name__ == "__main__":
    main()
