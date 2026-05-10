from __future__ import annotations

from pydantic import BaseModel


class MetricItem(BaseModel):
    label: str
    value: int | float


class DashboardOverview(BaseModel):
    total_papers: int
    abstracts_valid: int
    papers_classified: int
    unique_journals: int
    avg_abstract_length: float


class DistributionResponse(BaseModel):
    items: list[MetricItem]


class KeywordItem(BaseModel):
    keyword: str
    value: int


class LengthComparison(BaseModel):
    paper_length: int
    global_avg_length: float
    pb_avg_length: float


class PaperKeywordComparison(BaseModel):
    paper_keywords: list[str]
    paper_terms: list[str] = []
    global_overlap: list[KeywordItem]
    pb_overlap: list[KeywordItem]
    pb_terms_overlap: list[KeywordItem] = []
    global_top_keywords: list[KeywordItem]
    pb_top_keywords: list[KeywordItem]


class PaperComparisonResponse(BaseModel):
    paper_id: str
    title: str
    top_pb_code: str
    length_comparison: LengthComparison
    keyword_comparison: PaperKeywordComparison


class RuntimeMetricsResponse(BaseModel):
    cpu_pct: float
    ram_pct: float
    ram_used_mb: float
    ram_total_mb: float
    gpu_util_pct: float | None = None
    gpu_mem_util_pct: float | None = None
    gpu_power_w: float | None = None


# === Plan de entrega: KPIs y AED ===


class CorpusSummary(BaseModel):
    total_raw: int
    with_abstract: int
    valid: int
    for_embeddings: int
    indexed: int
    valid_pct: float
    embedding_pct: float
    embedding_pct_of_valid: float


class CorpusKPIs(CorpusSummary):
    avg_abstract_length: float
    median_abstract_length: float
    p90_abstract_length: float
    unique_journals: int
    papers_with_doi: int
    papers_with_keywords: int
    min_year: int | None
    max_year: int | None
    filter_rule: str
    embedding_text_rule: str


class LengthStats(BaseModel):
    mean: float
    median: float
    p25: float
    p75: float
    p90: float
    min: float
    max: float


class AbstractLengthDistribution(BaseModel):
    items: list[MetricItem]
    stats: LengthStats


class TemporalEvolutionItem(BaseModel):
    year: int
    valid: int
    for_embeddings: int


class MetadataCompletenessItem(BaseModel):
    field: str
    filled: int
    missing: int
    filled_pct: float


class DropReasonItem(BaseModel):
    reason: str
    count: int


class EmbeddingCoverage(BaseModel):
    valid_total: int
    embedding_total: int
    discarded_short_abstract: int
    embedding_text_length_stats: LengthStats
    abstract_length_stats: LengthStats
    approx_token_buckets: list[MetricItem]
    indexed_total: int
    coverage_vs_valid_pct: float
    filter_rule: str
    embedding_text_rule: str


class PBSimilarityCell(BaseModel):
    pb_a: str
    pb_b: str
    value: float


class PBSimilarityMatrix(BaseModel):
    metric: str
    pbs: list[str]
    cells: list[PBSimilarityCell]


class PBSimilarityPair(BaseModel):
    pb_a: str
    pb_b: str
    similarity: float


class PBComplexityItem(BaseModel):
    pb_code: str
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float


class PBTermItem(BaseModel):
    pb_code: str
    term: str
    value: float


class TopicClusterItem(BaseModel):
    cluster_id: int
    label: str
    n_docs: int
    pct_docs: float


class PBDocCountItem(BaseModel):
    pb_code: str
    n_docs: int


class PBTemporalItem(BaseModel):
    pb_code: str
    year: int
    value: int


class PBYearMatrix(BaseModel):
    pbs: list[str]
    years: list[int]
    cells: list[PBTemporalItem]


class EmbeddingMapPoint(BaseModel):
    doc_id: str
    title: str
    year: int | None
    pb_code: str
    x: float
    y: float


class EmbeddingMapBounds(BaseModel):
    xmin: float
    xmax: float
    ymin: float
    ymax: float


class EmbeddingMapResponse(BaseModel):
    available: bool
    points: list[EmbeddingMapPoint]
    pbs: list[str]
    bounds: EmbeddingMapBounds
    params: dict
    model_id: str | None
    total: int
    returned: int


class IndexStatus(BaseModel):
    model_id: str
    embedding_dim: int
    vectors: int
    candidates: int
    indexed_total: int
    is_built: bool
    is_specter: bool
    fallback_used: bool
    is_precomputed: bool = False
    source: str = "computed"
    embedding_text_rule: str
    filter_rule: str


class SimilarPaper(BaseModel):
    doc_id: str
    paper_id: str | None = None
    title: str
    year: int | None
    journal: str | None
    doi: str | None
    score: float
    abstract_preview: str
    pb_code: str | None
    keywords: list[str]
