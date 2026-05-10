import { AbstractComplexityTable } from "@/components/AbstractComplexityTable";
import { CleaningPipelineCard } from "@/components/CleaningPipelineCard";
import { CorpusLayersCard } from "@/components/CorpusLayersCard";
import { CorpusQualityPanel } from "@/components/CorpusQualityPanel";
import { KeywordsToggleCard } from "@/components/KeywordsToggleCard";
import { KpiCard } from "@/components/KpiCard";
import { MethodologyCallout } from "@/components/MethodologyCallout";
import { EmbeddingMap } from "@/components/charts/embedding-map";
import { PBStackedAreaChart } from "@/components/charts/pb-stacked-area";
import { PbFocusCard } from "@/components/PbFocusCard";
import { PbSimilarityHeatmap } from "@/components/PbSimilarityHeatmap";
import { PbWordcloudGallery } from "@/components/PbWordcloudGallery";
import { PbYearHeatmap } from "@/components/PbYearHeatmap";
import { TopicClustersCard } from "@/components/TopicClustersCard";
import {
  DistBarChart,
  DistLineChart,
  DistPieChart,
  HorizontalKeywordBars,
  TemporalQualityChart,
} from "@/components/charts/analytics-charts";
import { formatNumber, formatPercent, friendlyRule, modelLabel } from "@/components/format";
import { apiGet } from "@/lib/api";
import {
  AbstractLengthDistribution,
  CorpusKPIs,
  DistributionResponse,
  DropReasonItem,
  EmbeddingCoverage,
  IndexStatus,
  KeywordItem,
  MetadataCompletenessItem,
  PBComplexityItem,
  PBSimilarityMatrix,
  PBSimilarityPair,
  PBYearMatrix,
  TemporalEvolutionItem,
  TopicClusterItem,
} from "@/lib/types";

async function safe<T>(path: string, fallback: T): Promise<T> {
  try {
    return await apiGet<T>(path);
  } catch {
    return fallback;
  }
}

function SectionHeader({
  index,
  title,
  description,
}: {
  index: string;
  title: string;
  description: string;
}) {
  return (
    <header className="space-y-1">
      <p className="section-title text-emerald-400">{index}</p>
      <h2 className="text-2xl font-semibold tracking-tight text-textMain">{title}</h2>
      <p className="max-w-3xl text-sm leading-relaxed text-textSubtle">{description}</p>
    </header>
  );
}

function ChartCaption({ children }: { children: React.ReactNode }) {
  return <p className="help-text border-t border-line/60 pt-3">{children}</p>;
}

function friendlyDropReason(reason: string): string {
  const map: Record<string, string> = {
    "abstract_too_short<500": "Abstract demasiado corto (< 500 caracteres)",
    "abstract_empty|language_unknown": "Abstract vacío con idioma no determinable",
    "language_not_english:fr": "No está en inglés (francés)",
    "language_not_english:es": "No está en inglés (español)",
    "language_not_english:de": "No está en inglés (alemán)",
    "language_not_english:it": "No está en inglés (italiano)",
    "language_not_english:pt": "No está en inglés (portugués)",
    "language_not_english:ru": "No está en inglés (ruso)",
    "language_not_english:ro": "No está en inglés (rumano)",
    "language_low_confidence:0.55": "Idioma con baja confianza (0.55)",
    "language_low_confidence:0.57": "Idioma con baja confianza (0.57)",
  };
  if (map[reason]) return map[reason];
  if (reason.includes("abstract_too_short") && reason.includes("language_not_english")) {
    return "Abstract corto · idioma no inglés";
  }
  return reason;
}

export default async function AnalysisPage() {
  const [
    summary,
    coverage,
    indexStatus,
    abstractLengths,
    yearsValid,
    yearsEmbeddings,
    temporal,
    pbDistribution,
    keywords,
    unigrams,
    journals,
    metadata,
    drops,
    bigrams,
    wordsPerAbstract,
    pbYearMatrix,
    pbSimEmbeddings,
    pbSimTfidf,
    pbSimTopPairs,
    pbComplexity,
    topicClusters,
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
    safe<DistributionResponse>("/analytics/papers-by-year", { items: [] }),
    safe<DistributionResponse>("/analytics/papers-by-year/embeddings", { items: [] }),
    safe<TemporalEvolutionItem[]>("/analytics/papers-by-year/temporal-quality", []),
    safe<DistributionResponse>("/analytics/distribution/pb", { items: [] }),
    safe<KeywordItem[]>("/analytics/top-keywords?limit=15", []),
    safe<KeywordItem[]>("/analytics/top-unigrams?limit=15", []),
    safe<{ label: string; value: number }[]>("/analytics/top-journals?limit=10", []),
    safe<MetadataCompletenessItem[]>("/analytics/metadata-completeness", []),
    safe<DropReasonItem[]>("/analytics/drop-reasons", []),
    safe<KeywordItem[]>("/analytics/top-bigrams?limit=15", []),
    safe<DistributionResponse>("/analytics/words-per-abstract", { items: [] }),
    safe<PBYearMatrix>("/analytics/pb/year-matrix", { pbs: [], years: [], cells: [] }),
    safe<PBSimilarityMatrix>("/analytics/pb/similarity?metric=embeddings", {
      metric: "embeddings",
      pbs: [],
      cells: [],
    }),
    safe<PBSimilarityMatrix>("/analytics/pb/similarity?metric=tfidf", {
      metric: "tfidf",
      pbs: [],
      cells: [],
    }),
    safe<PBSimilarityPair[]>("/analytics/pb/similarity/top-pairs?metric=embeddings&limit=8", []),
    safe<PBComplexityItem[]>("/analytics/pb/abstract-complexity", []),
    safe<TopicClusterItem[]>("/analytics/topics/clusters", []),
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

  const yearRange = summary.min_year && summary.max_year ? `${summary.min_year} – ${summary.max_year}` : "—";
  const wordcloudItems = pbDistribution.items.map((item) => ({
    pb_code: item.label,
    count: item.value,
  }));

  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <span className="chip-accent">AED · Análisis exploratorio del corpus</span>
        <h1 className="text-3xl font-semibold tracking-tight text-balance lg:text-4xl">
          Diagnóstico del corpus UPV-EARTH
        </h1>
        <p className="max-w-3xl text-base leading-relaxed text-textSubtle">
          Esta página recorre, en orden, calidad temporal, calidad del corpus, metadatos, contenido textual y
          Planetary Boundaries. Cada bloque deja explícito qué métrica se calcula sobre qué capa: corpus bruto,
          con abstract, pasa filtros del pipeline, corpus válido SPECTER2 e indexado.
        </p>
      </header>

      <MethodologyCallout
        modelId={modelLabel(indexStatus.model_id)}
        isSpecter={indexStatus.is_specter}
        fallbackUsed={indexStatus.fallback_used}
      />

      <section className="space-y-4">
        <SectionHeader
          index="01 · Resumen ejecutivo"
          title="¿Qué papers entran realmente al pipeline SPECTER2?"
          description="Vista compacta de las cinco capas del corpus. El corpus válido del producto es la capa SPECTER2: papers cuyo abstract limpio supera 500 caracteres. La capa intermedia 'pasa filtros del pipeline' incluye papers con abstract crudo > 500 que tras la limpieza semántica se quedan cortos."
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Corpus bruto" value={summary.total_raw} helperBadge="bruto" helper="PDFs procesados sin filtros." />
          <KpiCard
            label="Pasa filtros pipeline"
            value={summary.valid}
            helperBadge={`${formatPercent(summary.valid_pct)}`}
            helper="Idioma + dedupe + abstract crudo > 500."
          />
          <KpiCard
            label="Corpus válido SPECTER2"
            value={summary.for_embeddings}
            helperBadge={`${formatPercent(summary.embedding_pct_of_valid)} sobre filtros`}
            helperTone="accent"
            helper="Abstract limpio con más de 500 caracteres."
            highlight
          />
          <KpiCard label="Rango temporal" value={yearRange} valueFormat="raw" helper={`${formatNumber(summary.unique_journals)} journals distintos`} />
        </div>
        <CorpusLayersCard data={cleanSummary} />
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="02 · Preparación para SPECTER2"
          title="Qué limpieza recibe cada paper antes del embedding"
          description="Detalle de las transformaciones aplicadas al texto antes de generar el vector. La metodología busca dejar la entrada del modelo libre de ruido bibliográfico, citas y secciones residuales para que la similitud refleje contenido científico."
        />
        <CleaningPipelineCard />
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="03 · Distribución temporal"
          title="Crecimiento histórico del corpus"
          description="Comparativa entre el corpus válido y el subconjunto apto para embeddings, año a año. La diferencia revela en qué períodos los abstracts cortos restan papers al índice SPECTER2."
        />
        <article className="card space-y-3">
          <TemporalQualityChart data={temporal} />
          <ChartCaption>
            Las áreas representan el conteo anual de papers. La sombra inferior es el subconjunto que cumple el
            criterio de calidad (abstract limpio &gt; 500 caracteres) y por tanto entra al índice de similitud.
          </ChartCaption>
        </article>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className="card space-y-3">
            <header>
              <p className="section-title">Papers válidos por año</p>
              <h3 className="text-lg font-semibold">Frecuencia anual</h3>
            </header>
            <DistLineChart data={yearsValid.items} />
            <ChartCaption>
              Conteo de papers en el corpus válido por año. Se ignoran años fuera de [1900, 2024] para evitar
              valores imposibles o mal parseados.
            </ChartCaption>
          </article>
          <article className="card space-y-3">
            <header>
              <p className="section-title">Aptos para embeddings por año</p>
              <h3 className="text-lg font-semibold">Sub-corpus SPECTER2</h3>
            </header>
            <DistLineChart data={yearsEmbeddings.items} />
            <ChartCaption>
              Mismo eje temporal, restringido a papers con abstract limpio de más de 500 caracteres.
            </ChartCaption>
          </article>
        </div>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="04 · Calidad del corpus"
          title="Distribución de longitud y motivos de descarte"
          description="Cuánto contenido tiene cada paper, qué buckets de longitud dominan y qué razones explican que algunos papers no superen el filtro metodológico."
        />
        <div className="grid gap-4 lg:grid-cols-3">
          <article className="card lg:col-span-2 space-y-3">
            <header className="flex items-center justify-between">
              <div>
                <p className="section-title">Longitud de abstracts</p>
                <h3 className="text-lg font-semibold">Histograma sobre el corpus válido</h3>
              </div>
              <span className="chip">criterio: abstract &gt; 500 caracteres</span>
            </header>
            <DistBarChart data={abstractLengths.items} />
            <ChartCaption>
              Las barras de 0-200 y 200-500 quedan fuera del índice SPECTER2.{" "}
              {abstractLengths.stats && (
                <>
                  Media {formatNumber(abstractLengths.stats.mean, 0)} caracteres, mediana{" "}
                  {formatNumber(abstractLengths.stats.median, 0)}, p90{" "}
                  {formatNumber(abstractLengths.stats.p90, 0)}.
                </>
              )}
            </ChartCaption>
          </article>
          <article className="card space-y-3">
            <header>
              <p className="section-title">Estadísticas de longitud</p>
              <h3 className="text-lg font-semibold">Resumen rápido</h3>
            </header>
            <ul className="space-y-2 text-sm">
              {[
                ["mean", "Media"],
                ["median", "Mediana"],
                ["p25", "Percentil 25"],
                ["p75", "Percentil 75"],
                ["p90", "Percentil 90"],
                ["min", "Mínimo"],
                ["max", "Máximo"],
              ].map(([key, label]) => {
                const value = abstractLengths.stats[key as keyof typeof abstractLengths.stats];
                return (
                  <li key={key} className="flex items-center justify-between rounded-xl border border-line/60 bg-surface-2 px-3 py-2">
                    <span className="text-textSubtle">{label}</span>
                    <span className="font-mono text-textMain">{formatNumber(Number(value || 0), 0)}</span>
                  </li>
                );
              })}
            </ul>
          </article>
        </div>

        <article className="card space-y-3">
          <header className="flex items-center justify-between">
            <div>
              <p className="section-title">Motivos de descarte</p>
              <h3 className="text-lg font-semibold">¿Por qué se cae un paper del corpus válido?</h3>
            </div>
            <span className="chip">trazabilidad</span>
          </header>
          <ul className="grid gap-2 md:grid-cols-2">
            {drops.length === 0 && (
              <li className="text-sm text-textMuted">No hay drops registrados en la trazabilidad.</li>
            )}
            {drops.map((item) => (
              <li
                key={item.reason}
                className="flex items-center justify-between rounded-xl border border-line/60 bg-surface-2 px-4 py-2 text-sm"
              >
                <span className="text-textSubtle">{friendlyDropReason(item.reason)}</span>
                <span className="font-mono text-textMain">{formatNumber(item.count)}</span>
              </li>
            ))}
          </ul>
          <ChartCaption>
            Los conteos provienen del CSV de trazabilidad y reflejan combinaciones de filtros. La razón dominante es
            el abstract corto, alineado con el filtro metodológico de la plataforma.
          </ChartCaption>
        </article>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="05 · Calidad del corpus para embeddings"
          title="Cobertura SPECTER2"
          description="Bloque obligatorio del plan de entrega. Hace explícito cuánto del corpus sirve realmente para embeddings y qué modelo está activo."
        />
        <CorpusQualityPanel coverage={cleanCoverage} index={cleanIndex} />
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="06 · Metadatos"
          title="Cobertura de campos auxiliares"
          description="Vista de qué campos están disponibles para análisis posterior (DOI, journal, keywords, año, idioma)."
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <article className="card space-y-3">
            <header>
              <p className="section-title">Completitud</p>
              <h3 className="text-lg font-semibold">Porcentaje de papers válidos con cada campo</h3>
            </header>
            <ul className="space-y-2 text-sm">
              {metadata.map((item) => (
                <li key={item.field} className="flex items-center gap-3">
                  <span className="w-24 text-textSubtle">{item.field}</span>
                  <div className="flex-1 overflow-hidden rounded-full bg-surface-2">
                    <div className="h-2.5 rounded-full bg-emerald-500/70" style={{ width: `${Math.min(100, item.filled_pct)}%` }} />
                  </div>
                  <span className="w-12 text-right font-mono text-textMain">{formatPercent(item.filled_pct, 1)}</span>
                  <span className="hidden w-24 text-right text-xs text-textMuted md:inline-block">
                    {formatNumber(item.filled)} / {formatNumber(item.filled + item.missing)}
                  </span>
                </li>
              ))}
            </ul>
            <ChartCaption>
              Los porcentajes se calculan sobre el corpus válido. Cuanto mayor el porcentaje, más fiable es analizar
              ese campo a nivel agregado.
            </ChartCaption>
          </article>
          <article className="card space-y-3">
            <header>
              <p className="section-title">Top journals</p>
              <h3 className="text-lg font-semibold">Concentración editorial</h3>
            </header>
            <HorizontalKeywordBars data={journals.map((item) => ({ keyword: item.label, value: item.value }))} />
            <ChartCaption>
              Algunos papers comparten el mismo nombre de journal genérico (por ejemplo &quot;untitled&quot;). Eso refleja el ruido
              de los metadatos originales, no un sesgo introducido por la plataforma.
            </ChartCaption>
          </article>
        </div>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="07 · Texto"
          title="Léxico, bigramas y densidad del abstract"
          description="Cómo de denso es el corpus en contenido textual y qué temas dominan a nivel de unigrama, bigrama y keyword declarada."
        />
        <KeywordsToggleCard declared={keywords} unigrams={unigrams} />
        <div className="grid gap-4 lg:grid-cols-2">
          <article className="card space-y-3">
            <header>
              <p className="section-title">Top bigramas</p>
              <h3 className="text-lg font-semibold">Pares de palabras frecuentes</h3>
            </header>
            <HorizontalKeywordBars data={bigrams} />
            <ChartCaption>
              Pares calculados sobre los abstracts del corpus. Aportan señal temática que no aparece a nivel de
              unigrama (p. ej. <em>climate change</em>, <em>ocean acidification</em>).
            </ChartCaption>
          </article>
          <article className="card space-y-3">
            <header>
              <p className="section-title">Distribución de palabras por abstract</p>
              <h3 className="text-lg font-semibold">Densidad textual del corpus</h3>
            </header>
            <DistBarChart data={wordsPerAbstract.items} />
            <ChartCaption>
              Histograma del número de palabras por abstract limpio. Los buckets bajos corresponden a papers con
              abstract escueto.
            </ChartCaption>
          </article>
        </div>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="08 · Planetary Boundaries"
          title="Cobertura, foco temático y evolución temporal"
          description="Distribución del top-PB asignado por similitud, perfil de keywords por PB y matriz PB × año del corpus indexado."
        />
        <article className="card space-y-3">
          <header>
            <p className="section-title">Ranking de PBs</p>
            <h3 className="text-lg font-semibold">Distribución del top-PB sobre el corpus indexado</h3>
          </header>
          <DistPieChart data={pbDistribution.items} />
          <ChartCaption>
            Asignación por similitud SPECTER2 entre el embedding del paper y los catálogos PB curados por UPV.
          </ChartCaption>
        </article>

        <PbFocusCard />

        <article className="card space-y-4">
          <header className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="section-title">Wordcloud por PB</p>
              <h3 className="text-lg font-semibold">Vocabulario dominante de cada Planetary Boundary</h3>
            </div>
            <span className="chip">precalculado · EDA</span>
          </header>
          <PbWordcloudGallery items={wordcloudItems} />
          <ChartCaption>
            Cada wordcloud se generó sobre los abstracts limpios del PB, ponderando por TF-IDF. Permite ver de un
            vistazo la jerga característica de cada Planetary Boundary.
          </ChartCaption>
        </article>

        <article className="card space-y-3">
          <header>
            <p className="section-title">Matriz PB × año</p>
            <h3 className="text-lg font-semibold">Heatmap de cobertura temporal por PB</h3>
          </header>
          <PbYearHeatmap matrix={pbYearMatrix} />
          <ChartCaption>
            Cada celda es el número de papers en el corpus indexado para ese PB en ese año. Verde más intenso = más
            papers. Permite ver picos de actividad por área (p. ej. clima 2010-2020).
          </ChartCaption>
        </article>

        <article className="card space-y-3">
          <header>
            <p className="section-title">Co-ocurrencia entre PBs (semántica)</p>
            <h3 className="text-lg font-semibold">Similitud SPECTER2 entre Planetary Boundaries</h3>
          </header>
          <PbSimilarityHeatmap matrix={pbSimEmbeddings} topPairs={pbSimTopPairs} />
          <ChartCaption>
            Matriz de similitud coseno calculada sobre los embeddings semánticos agregados por PB. Los pares más
            altos suelen reflejar overlap temático real (clima ↔ uso del suelo, ozono ↔ aerosoles).
          </ChartCaption>
        </article>

        <article className="card space-y-3">
          <header>
            <p className="section-title">Co-ocurrencia entre PBs (TF-IDF)</p>
            <h3 className="text-lg font-semibold">Similitud léxica por términos TF-IDF</h3>
          </header>
          <PbSimilarityHeatmap matrix={pbSimTfidf} topPairs={[]} />
          <ChartCaption>
            Misma idea pero con vectores TF-IDF: mide cuánto comparten vocabulario específico. Suele dar valores
            más bajos que la versión semántica porque ignora paráfrasis y sinónimos.
          </ChartCaption>
        </article>

        <article className="card space-y-3">
          <header>
            <p className="section-title">Complejidad del abstract por PB</p>
            <h3 className="text-lg font-semibold">Estadísticos descriptivos de longitud</h3>
          </header>
          <AbstractComplexityTable items={pbComplexity} />
          <ChartCaption>
            Estadísticos descriptivos de la longitud (en palabras) del abstract limpio agrupados por Planetary
            Boundary. PBs con mayor desviación típica son los más heterogéneos en cuanto a densidad textual.
          </ChartCaption>
        </article>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="09 · Topics semánticos"
          title="Clusters automáticos sobre embeddings del corpus"
          description="Agrupación no supervisada de papers por similitud semántica. Permite identificar agendas temáticas que cruzan PBs y ver el peso relativo de cada agenda."
        />
        <article className="card space-y-3">
          <TopicClustersCard items={topicClusters} />
          <ChartCaption>
            Topics descubiertos automáticamente sobre el corpus mediante agrupación no supervisada de embeddings
            semánticos. Los temas se etiquetan con sus términos más representativos.
          </ChartCaption>
        </article>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="10 · Evolución acumulada por PB"
          title="Producción anual del corpus apilada por Planetary Boundary"
          description="Series temporales apiladas: cuánto se publicó cada año y cómo se reparte entre los nueve PB. Sirve para ver el crecimiento global y qué PB ha ganado peso en cada década."
        />
        <article className="card space-y-3">
          <PBStackedAreaChart data={pbYearMatrix} minYear={1990} height={420} />
          <ChartCaption>
            Cada banda coloreada es un PB; la altura total del área en un año es el total de papers
            indexados ese año en el corpus UPV. Cobertura: corpus indexado (abstract limpio &gt; 500 caracteres).
          </ChartCaption>
        </article>
      </section>

      <section className="space-y-4">
        <SectionHeader
          index="11 · Mapa 2D del corpus"
          title="Proyección UMAP de los embeddings SPECTER2 coloreada por PB"
          description="Reducción no lineal a 2D del espacio semántico. Cada punto es un paper; clusters próximos comparten temática. Pasa el ratón por encima para ver título, año y PB asignado."
        />
        <article className="card space-y-3">
          <EmbeddingMap sample={6000} height={520} />
          <ChartCaption>
            UMAP (cosine, n_neighbors auto, min_dist=0.1) sobre los 30 508 embeddings SPECTER2
            del corpus indexado. Mostramos un sub-muestreo determinista para que el navegador
            renderice fluido; la distribución espacial se preserva.
          </ChartCaption>
        </article>
      </section>
    </div>
  );
}
