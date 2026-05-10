export type MetricItem = {
  label: string;
  value: number;
};

export type Overview = {
  total_papers: number;
  abstracts_valid: number;
  papers_classified: number;
  unique_journals: number;
  avg_abstract_length: number;
};

export type CorpusKPIs = {
  total_raw: number;
  with_abstract: number;
  valid: number;
  for_embeddings: number;
  indexed: number;
  valid_pct: number;
  embedding_pct: number;
  embedding_pct_of_valid: number;
  avg_abstract_length: number;
  median_abstract_length: number;
  p90_abstract_length: number;
  unique_journals: number;
  papers_with_doi: number;
  papers_with_keywords: number;
  min_year: number | null;
  max_year: number | null;
  filter_rule: string;
  embedding_text_rule: string;
};

export type LengthStats = {
  mean: number;
  median: number;
  p25: number;
  p75: number;
  p90: number;
  min: number;
  max: number;
};

export type AbstractLengthDistribution = {
  items: MetricItem[];
  stats: LengthStats;
};

export type TemporalEvolutionItem = {
  year: number;
  valid: number;
  for_embeddings: number;
};

export type MetadataCompletenessItem = {
  field: string;
  filled: number;
  missing: number;
  filled_pct: number;
};

export type DropReasonItem = {
  reason: string;
  count: number;
};

export type EmbeddingCoverage = {
  valid_total: number;
  embedding_total: number;
  discarded_short_abstract: number;
  embedding_text_length_stats: LengthStats;
  abstract_length_stats: LengthStats;
  approx_token_buckets: MetricItem[];
  indexed_total: number;
  coverage_vs_valid_pct: number;
  filter_rule: string;
  embedding_text_rule: string;
};

export type IndexStatus = {
  model_id: string;
  embedding_dim: number;
  vectors: number;
  candidates: number;
  indexed_total: number;
  is_built: boolean;
  is_specter: boolean;
  fallback_used: boolean;
  is_precomputed: boolean;
  source: string;
  embedding_text_rule: string;
  filter_rule: string;
};

export type PBTemporalItem = {
  pb_code: string;
  year: number;
  value: number;
};

export type PBYearMatrix = {
  pbs: string[];
  years: number[];
  cells: PBTemporalItem[];
};

export type PBSimilarityCell = {
  pb_a: string;
  pb_b: string;
  value: number;
};

export type PBSimilarityMatrix = {
  metric: string;
  pbs: string[];
  cells: PBSimilarityCell[];
};

export type PBSimilarityPair = {
  pb_a: string;
  pb_b: string;
  similarity: number;
};

export type PBComplexityItem = {
  pb_code: string;
  count: number;
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
};

export type PBTermItem = {
  pb_code: string;
  term: string;
  value: number;
};

export type TopicClusterItem = {
  cluster_id: number;
  label: string;
  n_docs: number;
  pct_docs: number;
};

export type DownloadItem = {
  name: string;
  description: string;
  path: string;
  category: string;
};

export type SimilarPaper = {
  doc_id: string;
  paper_id: string | null;
  title: string;
  year: number | null;
  journal: string | null;
  doi: string | null;
  score: number;
  abstract_preview: string;
  pb_code: string | null;
  keywords: string[];
};

export type PBResult = {
  top_pb_code: string;
  top_pb_score: number;
  secondary_pbs: Array<{ pb_code: string; pb_name?: string; score: number }> | Record<string, unknown>;
  score_map: Record<string, number>;
  explanation_text: string;
};

export type Paper = {
  id: string;
  doc_id: string | null;
  title: string;
  abstract_norm: string;
  year: number | null;
  doi: string | null;
  source: string | null;
  journal: string | null;
  keywords: string | null;
  pb_result: PBResult | null;
  abstract_char_len: number;
  is_valid_for_embedding: boolean;
};

export type PaperListResponse = {
  total: number;
  page: number;
  page_size: number;
  items: Paper[];
};

export type DistributionResponse = {
  items: MetricItem[];
};

export type KeywordItem = {
  keyword: string;
  value: number;
};

export type LengthComparison = {
  paper_length: number;
  global_avg_length: number;
  pb_avg_length: number;
};

export type PaperKeywordComparison = {
  paper_keywords: string[];
  paper_terms: string[];
  global_overlap: KeywordItem[];
  pb_overlap: KeywordItem[];
  pb_terms_overlap: KeywordItem[];
  global_top_keywords: KeywordItem[];
  pb_top_keywords: KeywordItem[];
};

export type PaperComparison = {
  paper_id: string;
  title: string;
  top_pb_code: string;
  length_comparison: LengthComparison;
  keyword_comparison: PaperKeywordComparison;
};

export type Job = {
  id: string;
  paper_id: string | null;
  filename_original: string;
  status: string;
  stage: string;
  progress_pct: number;
  error_code: string | null;
  error_message: string | null;
};

export type AbstractValidation = {
  abstract_detected: boolean;
  abstract_char_len: number;
  threshold: number;
  passes_threshold: boolean;
  is_valid_for_embedding: boolean;
};

export type EmbeddingInfo = {
  model_id: string;
  family: string;
  is_specter: boolean;
  embedding_dim: number | null;
  embedding_text_rule: string;
  embedding_text_preview: string | null;
  fallback_used: boolean;
};

export type JobResult = {
  job: Job;
  abstract_detected: string | null;
  abstract_validation: AbstractValidation | null;
  embedding_info: EmbeddingInfo | null;
  summary: string | null;
  pb_result: PBResult | null;
  similar_papers: SimilarPaper[];
};

export type RuntimeMetrics = {
  cpu_pct?: number | null;
  ram_pct?: number | null;
  ram_used_mb?: number | null;
  ram_total_mb?: number | null;
  gpu_util_pct?: number | null;
  gpu_mem_util_pct?: number | null;
  gpu_power_w?: number | null;
};

export type JobEvent = {
  id: string;
  job_id: string;
  event_type: string;
  event_payload: Record<string, unknown> & RuntimeMetrics;
  created_at: string | null;
};

export type ChatHealth = {
  enabled: boolean;
  available: boolean;
  model: string | null;
  base_url: string | null;
  reason: string | null;
};

export type ChatContextSummary = {
  has_paper: boolean;
  has_pb_result: boolean;
  similar_count: number;
  pb_catalog_count: number;
  methodology_count: number;
  has_analytics: boolean;
  paper_title: string | null;
};

export type ChatResponse = {
  enabled: boolean;
  available: boolean;
  text: string;
  error: string | null;
  model: string | null;
  duration_sec: number | null;
  context: ChatContextSummary;
};

export type EmbeddingMapPoint = {
  doc_id: string;
  title: string;
  year: number | null;
  pb_code: string;
  x: number;
  y: number;
};

export type EmbeddingMapResponse = {
  available: boolean;
  points: EmbeddingMapPoint[];
  pbs: string[];
  bounds: { xmin: number; xmax: number; ymin: number; ymax: number };
  params: Record<string, unknown>;
  model_id: string | null;
  total: number;
  returned: number;
};

export type PBYearMatrix = {
  pbs: string[];
  years: number[];
  cells: { pb_code: string; year: number; value: number }[];
};
