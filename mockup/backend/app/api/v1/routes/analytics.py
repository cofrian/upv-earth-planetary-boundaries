from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import (
    AbstractLengthDistribution,
    CorpusKPIs,
    CorpusSummary,
    DashboardOverview,
    DistributionResponse,
    DropReasonItem,
    EmbeddingCoverage,
    EmbeddingMapPoint,
    EmbeddingMapResponse,
    IndexStatus,
    KeywordItem,
    LengthStats,
    MetadataCompletenessItem,
    MetricItem,
    PBComplexityItem,
    PBDocCountItem,
    PBSimilarityCell,
    PBSimilarityMatrix,
    PBSimilarityPair,
    PBTemporalItem,
    PBTermItem,
    PBYearMatrix,
    PaperComparisonResponse,
    RuntimeMetricsResponse,
    TemporalEvolutionItem,
    TopicClusterItem,
)
from app.services.models_benchmark.service import models_benchmark
from app.services.eda_artifacts.service import (
    abstract_complexity_by_pb,
    pb_doc_counts as eda_pb_doc_counts,
    pb_similarity_matrix,
    pb_similarity_top_pairs,
    semantic_topic_summary,
    tfidf_terms_by_pb,
    wordcloud_image_path,
    wordcloud_terms_by_pb,
)
from app.services.analytics_service.service import (
    distribution_by_abstract_length,
    distribution_by_pb,
    distribution_by_source,
    distribution_by_year,
    overview,
    paper_comparison,
    pb_temporal_evolution,
    pb_year_matrix,
    top_keywords_by_pb,
    top_keywords_global,
)
from app.services.corpus_quality.service import (
    abstract_length_distribution,
    drop_reasons,
    embedding_coverage,
    metadata_completeness,
    overview_kpis,
    papers_by_year_distribution,
    papers_by_year_for_embeddings_distribution,
    temporal_quality_evolution,
    top_bigrams,
    top_journals,
    top_keywords_corpus,
    top_unigrams,
    words_per_abstract_distribution,
)
from app.services.similarity_search.service import index_status
from app.services.embedding_map.service import (
    get_map_payload,
    get_paper_position,
)
from app.services.system_metrics import collect_system_metrics

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db)) -> DashboardOverview:
    return DashboardOverview(**overview(db))


@router.get("/distribution/pb", response_model=DistributionResponse)
def get_pb_distribution(db: Session = Depends(get_db)) -> DistributionResponse:
    return DistributionResponse(items=distribution_by_pb(db))


@router.get("/distribution/year", response_model=DistributionResponse)
def get_year_distribution(db: Session = Depends(get_db)) -> DistributionResponse:
    return DistributionResponse(items=distribution_by_year(db))


@router.get("/distribution/source", response_model=DistributionResponse)
def get_source_distribution(db: Session = Depends(get_db)) -> DistributionResponse:
    return DistributionResponse(items=distribution_by_source(db))


@router.get("/distribution/abstract-length", response_model=DistributionResponse)
def get_abstract_length_distribution(db: Session = Depends(get_db)) -> DistributionResponse:
    return DistributionResponse(items=distribution_by_abstract_length(db))


@router.get("/keywords/global", response_model=list[KeywordItem])
def get_global_keywords(
    limit: int = Query(default=20, ge=5, le=50),
    db: Session = Depends(get_db),
) -> list[KeywordItem]:
    return [KeywordItem(**item) for item in top_keywords_global(db, limit=limit)]


@router.get("/keywords/pb/{pb_code}", response_model=list[KeywordItem])
def get_pb_keywords(
    pb_code: str,
    limit: int = Query(default=20, ge=5, le=50),
    db: Session = Depends(get_db),
) -> list[KeywordItem]:
    return [KeywordItem(**item) for item in top_keywords_by_pb(db, pb_code=pb_code, limit=limit)]


@router.get("/papers/{paper_id}/comparison", response_model=PaperComparisonResponse)
def get_paper_comparison(paper_id: uuid.UUID, db: Session = Depends(get_db)) -> PaperComparisonResponse:
    payload = paper_comparison(db, paper_id=paper_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return PaperComparisonResponse(**payload)


@router.get("/runtime/metrics", response_model=RuntimeMetricsResponse)
def get_runtime_metrics() -> RuntimeMetricsResponse:
    return RuntimeMetricsResponse(**collect_system_metrics())


# === Endpoints de calidad de corpus para Dashboard y AED ===


@router.get("/summary", response_model=CorpusKPIs)
def get_corpus_summary() -> CorpusKPIs:
    return CorpusKPIs(**overview_kpis())


@router.get("/corpus/layers", response_model=CorpusSummary)
def get_corpus_layers_summary() -> CorpusSummary:
    payload = overview_kpis()
    return CorpusSummary(
        total_raw=payload["total_raw"],
        with_abstract=payload["with_abstract"],
        valid=payload["valid"],
        for_embeddings=payload["for_embeddings"],
        indexed=payload["indexed"],
        valid_pct=payload["valid_pct"],
        embedding_pct=payload["embedding_pct"],
        embedding_pct_of_valid=payload["embedding_pct_of_valid"],
    )


@router.get("/abstract-lengths", response_model=AbstractLengthDistribution)
def get_abstract_lengths() -> AbstractLengthDistribution:
    payload = abstract_length_distribution()
    return AbstractLengthDistribution(
        items=[MetricItem(**item) for item in payload["items"]],
        stats=LengthStats(**payload["stats"]),
    )


@router.get("/papers-by-year", response_model=DistributionResponse)
def get_papers_by_year() -> DistributionResponse:
    return DistributionResponse(items=[MetricItem(**item) for item in papers_by_year_distribution()])


@router.get("/papers-by-year/embeddings", response_model=DistributionResponse)
def get_papers_by_year_embeddings() -> DistributionResponse:
    return DistributionResponse(
        items=[MetricItem(**item) for item in papers_by_year_for_embeddings_distribution()]
    )


@router.get("/papers-by-year/temporal-quality", response_model=list[TemporalEvolutionItem])
def get_papers_by_year_temporal_quality() -> list[TemporalEvolutionItem]:
    return [TemporalEvolutionItem(**item) for item in temporal_quality_evolution()]


@router.get("/metadata-completeness", response_model=list[MetadataCompletenessItem])
def get_metadata_completeness() -> list[MetadataCompletenessItem]:
    return [MetadataCompletenessItem(**item) for item in metadata_completeness()]


@router.get("/top-keywords", response_model=list[KeywordItem])
def get_top_keywords_corpus(limit: int = Query(default=20, ge=5, le=50)) -> list[KeywordItem]:
    return [KeywordItem(**item) for item in top_keywords_corpus(limit=limit)]


@router.get("/top-journals", response_model=list[MetricItem])
def get_top_journals(limit: int = Query(default=10, ge=5, le=50)) -> list[MetricItem]:
    return [MetricItem(**item) for item in top_journals(limit=limit)]


@router.get("/drop-reasons", response_model=list[DropReasonItem])
def get_drop_reasons() -> list[DropReasonItem]:
    return [DropReasonItem(**item) for item in drop_reasons()]


@router.get("/embedding-coverage", response_model=EmbeddingCoverage)
def get_embedding_coverage() -> EmbeddingCoverage:
    payload = embedding_coverage()
    return EmbeddingCoverage(
        valid_total=payload["valid_total"],
        embedding_total=payload["embedding_total"],
        discarded_short_abstract=payload["discarded_short_abstract"],
        embedding_text_length_stats=LengthStats(**payload["embedding_text_length_stats"]),
        abstract_length_stats=LengthStats(**payload["abstract_length_stats"]),
        approx_token_buckets=[MetricItem(**item) for item in payload["approx_token_buckets"]],
        indexed_total=payload["indexed_total"],
        coverage_vs_valid_pct=payload["coverage_vs_valid_pct"],
        filter_rule=payload["filter_rule"],
        embedding_text_rule=payload["embedding_text_rule"],
    )


@router.get("/index-status", response_model=IndexStatus)
def get_index_status() -> IndexStatus:
    return IndexStatus(**index_status())


@router.get("/top-bigrams", response_model=list[KeywordItem])
def get_top_bigrams(limit: int = Query(default=20, ge=5, le=50)) -> list[KeywordItem]:
    return [KeywordItem(**item) for item in top_bigrams(limit=limit)]


@router.get("/top-unigrams", response_model=list[KeywordItem])
def get_top_unigrams(limit: int = Query(default=20, ge=5, le=50)) -> list[KeywordItem]:
    return [KeywordItem(**item) for item in top_unigrams(limit=limit)]


@router.get("/words-per-abstract", response_model=DistributionResponse)
def get_words_per_abstract() -> DistributionResponse:
    return DistributionResponse(items=[MetricItem(**item) for item in words_per_abstract_distribution()])


@router.get("/pb/temporal", response_model=list[PBTemporalItem])
def get_pb_temporal(db: Session = Depends(get_db)) -> list[PBTemporalItem]:
    return [PBTemporalItem(**item) for item in pb_temporal_evolution(db)]


@router.get("/pb/year-matrix", response_model=PBYearMatrix)
def get_pb_year_matrix(db: Session = Depends(get_db)) -> PBYearMatrix:
    payload = pb_year_matrix(db)
    return PBYearMatrix(
        pbs=payload["pbs"],
        years=payload["years"],
        cells=[PBTemporalItem(**cell) for cell in payload["cells"]],
    )


@router.get("/embedding-map", response_model=EmbeddingMapResponse)
def get_embedding_map(
    sample: int = Query(default=8000, ge=200, le=40000),
) -> EmbeddingMapResponse:
    """Mapa 2D UMAP del corpus indexado.

    `sample` limita el número de puntos devueltos al frontend (Recharts
    rinde bien hasta ~10k). Se sub-muestrea de forma determinista para
    mantener la distribución espacial del mapa.
    """
    payload = get_map_payload(sample=sample)
    return EmbeddingMapResponse(
        available=payload["available"],
        points=[EmbeddingMapPoint(**p) for p in payload["points"]],
        pbs=payload["pbs"],
        bounds=payload["bounds"],
        params=payload["params"],
        model_id=payload["model_id"],
        total=payload["total"],
        returned=payload["returned"],
    )


@router.get("/embedding-map/paper", response_model=EmbeddingMapPoint)
def get_embedding_map_paper(doc_id: str = Query(..., min_length=4)) -> EmbeddingMapPoint:
    """Coordenadas 2D de un paper concreto en el mapa precomputado."""
    point = get_paper_position(doc_id)
    if point is None:
        raise HTTPException(status_code=404, detail="doc_id no presente en el mapa precomputado")
    return EmbeddingMapPoint(**point)


@router.get("/pb/similarity", response_model=PBSimilarityMatrix)
def get_pb_similarity(
    metric: str = Query(default="embeddings", regex="^(embeddings|tfidf|corpus)$"),
) -> PBSimilarityMatrix:
    payload = pb_similarity_matrix(metric)
    if not payload:
        raise HTTPException(status_code=404, detail=f"No hay matriz precalculada para '{metric}'.")
    return PBSimilarityMatrix(
        metric=payload["metric"],
        pbs=payload["pbs"],
        cells=[PBSimilarityCell(**cell) for cell in payload["cells"]],
    )


@router.get("/pb/similarity/top-pairs", response_model=list[PBSimilarityPair])
def get_pb_similarity_pairs(
    metric: str = Query(default="embeddings", regex="^(embeddings|tfidf|corpus)$"),
    limit: int = Query(default=10, ge=3, le=50),
) -> list[PBSimilarityPair]:
    return [PBSimilarityPair(**item) for item in pb_similarity_top_pairs(metric, limit=limit)]


@router.get("/pb/abstract-complexity", response_model=list[PBComplexityItem])
def get_pb_complexity() -> list[PBComplexityItem]:
    return [PBComplexityItem(**item) for item in abstract_complexity_by_pb()]


@router.get("/pb/tfidf-terms", response_model=list[PBTermItem])
def get_pb_tfidf_terms(
    pb_code: str | None = Query(default=None),
    limit: int = Query(default=10, ge=3, le=30),
) -> list[PBTermItem]:
    return [PBTermItem(**item) for item in tfidf_terms_by_pb(pb_code, limit=limit)]


@router.get("/pb/wordcloud-image")
def get_pb_wordcloud_image(
    pb_code: str = Query(..., description="Código del Planetary Boundary"),
) -> FileResponse:
    target = wordcloud_image_path(pb_code)
    if not target:
        raise HTTPException(status_code=404, detail="Wordcloud no disponible para este PB.")
    return FileResponse(target, media_type="image/png")


@router.get("/pb/wordcloud-terms", response_model=list[PBTermItem])
def get_pb_wordcloud_terms(
    pb_code: str | None = Query(default=None),
    limit: int = Query(default=20, ge=3, le=50),
) -> list[PBTermItem]:
    return [PBTermItem(**item) for item in wordcloud_terms_by_pb(pb_code, limit=limit)]


@router.get("/pb/doc-counts", response_model=list[PBDocCountItem])
def get_pb_doc_counts_eda() -> list[PBDocCountItem]:
    return [PBDocCountItem(**item) for item in eda_pb_doc_counts()]


@router.get("/topics/clusters", response_model=list[TopicClusterItem])
def get_topic_clusters() -> list[TopicClusterItem]:
    return [TopicClusterItem(**item) for item in semantic_topic_summary()]


@router.get("/models-benchmark", response_model=dict[str, Any])
def get_models_benchmark() -> dict[str, Any]:
    return models_benchmark()


@router.get("/downloads", response_model=list[dict[str, Any]])
def get_downloads_manifest() -> list[dict[str, Any]]:
    """Manifiesto de artefactos exportables (rutas relativas dentro del repo).

    No descarga binarios desde aquí, pero deja documentado dónde se
    generan los CSVs de trazabilidad y EDA.
    """
    return [
        {
            "name": "Corpus enriquecido",
            "description": "CSV maestro con corpus válido, abstracts limpios y columnas de soporte.",
            "path": "data/corpus/master_corpus_mixto_clean_enriched.csv",
            "category": "corpus",
        },
        {
            "name": "Trazabilidad",
            "description": "Auditoría de filtros aplicados (kept/dropped) con motivos y flags.",
            "path": "data/corpus/master_corpus_mixto_traceability.csv",
            "category": "corpus",
        },
        {
            "name": "Resumen EDA",
            "description": "Tabla de KPIs y descriptores agregados generados por scripts de EDA.",
            "path": "docs/eda/eda_summary.md",
            "category": "eda",
        },
        {
            "name": "Top unigrams",
            "description": "Términos más frecuentes en el corpus válido.",
            "path": "docs/eda/top_unigrams.csv",
            "category": "eda",
        },
        {
            "name": "Top bigrams",
            "description": "Bigramas más frecuentes en el corpus válido.",
            "path": "docs/eda/top_bigrams.csv",
            "category": "eda",
        },
        {
            "name": "Distribución por año",
            "description": "Conteo de papers válidos por año.",
            "path": "docs/eda/year_distribution.csv",
            "category": "eda",
        },
        {
            "name": "Combinaciones de motivos de descarte",
            "description": "Trazabilidad de papers descartados por filtro.",
            "path": "docs/eda/drop_reason_combinations.csv",
            "category": "eda",
        },
    ]
