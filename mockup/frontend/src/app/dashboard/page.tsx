import { CorpusLayersCard } from "@/components/CorpusLayersCard";
import { CorpusQualityPanel } from "@/components/CorpusQualityPanel";
import { KpiCard } from "@/components/KpiCard";
import { MethodologyCallout } from "@/components/MethodologyCallout";
import { PbFocusCard } from "@/components/PbFocusCard";
import {
  DistBarChart,
  DistPieChart,
  HorizontalKeywordBars,
  TemporalQualityChart,
} from "@/components/charts/analytics-charts";
import { formatPercent, friendlyRule, modelLabel } from "@/components/format";
import { apiGet } from "@/lib/api";
import {
  AbstractLengthDistribution,
  CorpusKPIs,
  DistributionResponse,
  EmbeddingCoverage,
  IndexStatus,
  KeywordItem,
  TemporalEvolutionItem,
} from "@/lib/types";

async function safe<T>(path: string, fallback: T): Promise<T> {
  try {
    return await apiGet<T>(path);
  } catch {
    return fallback;
  }
}

export default async function DashboardPage() {
  const [
    summary,
    coverage,
    indexStatus,
    abstractLengths,
    pbDistribution,
    temporal,
    keywords,
  ] = await Promise.all([
    safe<CorpusKPIs>("/analytics/summary", {
      total_raw: 0,
      with_abstract: 0,
      valid: 0,
      for_embeddings: 0,
      indexed: 0,
      valid_pct: 0,
      embedding_pct: 0,
      embedding_pct_of_valid: 0,
      avg_abstract_length: 0,
      median_abstract_length: 0,
      p90_abstract_length: 0,
      unique_journals: 0,
      papers_with_doi: 0,
      papers_with_keywords: 0,
      min_year: null,
      max_year: null,
      filter_rule: "abstract limpio > 500 caracteres",
      embedding_text_rule: "título + abstract limpio",
    }),
    safe<EmbeddingCoverage>("/analytics/embedding-coverage", {
      valid_total: 0,
      embedding_total: 0,
      discarded_short_abstract: 0,
      embedding_text_length_stats: { mean: 0, median: 0, p25: 0, p75: 0, p90: 0, min: 0, max: 0 },
      abstract_length_stats: { mean: 0, median: 0, p25: 0, p75: 0, p90: 0, min: 0, max: 0 },
      approx_token_buckets: [],
      indexed_total: 0,
      coverage_vs_valid_pct: 0,
      filter_rule: "abstract limpio > 500 caracteres",
      embedding_text_rule: "título + abstract limpio",
    }),
    safe<IndexStatus>("/analytics/index-status", {
      model_id: "—",
      embedding_dim: 0,
      vectors: 0,
      candidates: 0,
      indexed_total: 0,
      is_built: false,
      is_specter: false,
      fallback_used: false,
      is_precomputed: false,
      source: "computed",
      embedding_text_rule: "título + abstract limpio",
      filter_rule: "abstract limpio > 500 caracteres",
    }),
    safe<AbstractLengthDistribution>("/analytics/abstract-lengths", {
      items: [],
      stats: { mean: 0, median: 0, p25: 0, p75: 0, p90: 0, min: 0, max: 0 },
    }),
    safe<DistributionResponse>("/analytics/distribution/pb", { items: [] }),
    safe<TemporalEvolutionItem[]>("/analytics/papers-by-year/temporal-quality", []),
    safe<KeywordItem[]>("/analytics/top-keywords?limit=10", []),
  ]);

  const cleanSummary: CorpusKPIs = {
    ...summary,
    filter_rule: friendlyRule(summary.filter_rule),
    embedding_text_rule: friendlyRule(summary.embedding_text_rule),
  };
  const cleanCoverage: EmbeddingCoverage = {
    ...coverage,
    filter_rule: friendlyRule(coverage.filter_rule),
    embedding_text_rule: friendlyRule(coverage.embedding_text_rule),
  };
  const cleanIndex: IndexStatus = {
    ...indexStatus,
    model_id: modelLabel(indexStatus.model_id),
    embedding_text_rule: friendlyRule(indexStatus.embedding_text_rule),
    filter_rule: friendlyRule(indexStatus.filter_rule),
  };

  return (
    <div className="space-y-8">
      <section className="space-y-3 animate-fade-up">
        <span className="chip-accent">Producto científico · Entrega final</span>
        <h2 className="text-3xl font-semibold tracking-tight text-balance lg:text-4xl">
          Plataforma analítica del corpus UPV-EARTH
        </h2>
        <p className="max-w-3xl text-base leading-relaxed text-textSubtle">
          Pipeline reproducible con cinco capas explícitas: del corpus bruto al índice de similitud. El corpus
          válido del producto exige que el abstract limpio supere 500 caracteres y representa cada paper como
          título + abstract limpio antes de generar el embedding SPECTER2.
        </p>
      </section>

      <MethodologyCallout
        modelId={modelLabel(indexStatus.model_id)}
        isSpecter={indexStatus.is_specter}
        fallbackUsed={indexStatus.fallback_used}
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5 animate-fade-up">
        <KpiCard label="Corpus bruto" value={summary.total_raw} helperBadge="bruto" helper="Papers procesados sin filtros." />
        <KpiCard
          label="Con abstract"
          value={summary.with_abstract}
          helperBadge={`${formatPercent((summary.with_abstract / Math.max(1, summary.total_raw)) * 100)} del bruto`}
          helper="Algún abstract identificable tras parsing."
        />
        <KpiCard
          label="Pasa filtros pipeline"
          value={summary.valid}
          helperBadge={formatPercent(summary.valid_pct)}
          helper="Idioma comprobado, sin duplicados y abstract original suficiente."
        />
        <KpiCard
          label="Corpus válido SPECTER2"
          value={summary.for_embeddings}
          helperBadge={`${formatPercent(summary.embedding_pct_of_valid)} sobre filtros`}
          helperTone="accent"
          helper="Abstract limpio con más de 500 caracteres. Es el corpus del producto."
          highlight
        />
        <KpiCard
          label="Indexado en SPECTER2"
          value={summary.indexed}
          helperBadge="similitud lista"
          helperTone="accent"
          helper="Embeddings generados y disponibles para búsqueda."
        />
      </section>

      <CorpusLayersCard data={cleanSummary} />

      <article className="card space-y-4">
        <header className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <p className="section-title">Calidad temporal del corpus</p>
            <h3 className="text-lg font-semibold">Evolución por año: válido vs apto para embeddings</h3>
          </div>
          <span className="chip-accent">criterio: abstract &gt; 500</span>
        </header>
        <TemporalQualityChart data={temporal} />
        <p className="help-text">
          Las áreas comparan el conteo anual del corpus que pasa filtros contra el subconjunto que entra al índice
          SPECTER2.
        </p>
      </article>

      <CorpusQualityPanel coverage={cleanCoverage} index={cleanIndex} />

      <section className="grid gap-4 lg:grid-cols-5">
        <article className="card lg:col-span-3 space-y-3">
          <header className="flex items-center justify-between">
            <div>
              <p className="section-title">Distribución de longitud de abstract</p>
              <h3 className="text-lg font-semibold">Apto para embeddings cuando supera 500 caracteres</h3>
            </div>
            <span className="chip">corpus que pasa filtros</span>
          </header>
          <DistBarChart data={abstractLengths.items} />
          <p className="help-text">
            Histograma de longitud del abstract limpio. Los buckets a la izquierda del umbral de 500 caracteres
            quedan fuera del corpus SPECTER2.
          </p>
        </article>
        <article className="card lg:col-span-2 space-y-3">
          <header>
            <p className="section-title">Planetary Boundaries</p>
            <h3 className="text-lg font-semibold">Distribución del top-PB</h3>
          </header>
          <DistPieChart data={pbDistribution.items} />
          <p className="help-text">Asignación por similitud SPECTER2 contra los catálogos PB de UPV.</p>
        </article>
      </section>

      <PbFocusCard />

      <section className="card space-y-3">
        <header>
          <p className="section-title">Top keywords del corpus</p>
          <h3 className="text-lg font-semibold">Términos más frecuentes en el corpus</h3>
        </header>
        <HorizontalKeywordBars data={keywords} />
      </section>
    </div>
  );
}
