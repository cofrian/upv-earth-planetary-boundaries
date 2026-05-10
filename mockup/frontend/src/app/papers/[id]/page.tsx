import Link from "next/link";

import { AbstractValidationCard } from "@/components/AbstractValidationCard";
import { KeywordsWithMatches } from "@/components/KeywordsWithMatches";
import { KpiCard } from "@/components/KpiCard";
import { PaperChatScope } from "@/components/PaperChatScope";
import { PaperOverlapCard } from "@/components/PaperOverlapCard";
import { SimilarPapersList } from "@/components/SimilarPapersList";
import { LengthComparisonChart, HorizontalKeywordBars } from "@/components/charts/analytics-charts";
import { EmbeddingMap } from "@/components/charts/embedding-map";
import { formatNumber, modelLabel } from "@/components/format";
import { apiGet } from "@/lib/api";
import { IndexStatus, Paper, PaperComparison, SimilarPaper } from "@/lib/types";

async function safe<T>(path: string, fallback: T): Promise<T> {
  try {
    return await apiGet<T>(path);
  } catch {
    return fallback;
  }
}

export default async function PaperDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const [paper, indexStatus] = await Promise.all([
    apiGet<Paper>(`/papers/${id}`),
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
      filter_rule: "abstract > 500 caracteres",
    }),
  ]);

  const [comparison, similar] = await Promise.all([
    safe<PaperComparison | null>(`/analytics/papers/${id}/comparison`, null),
    safe<SimilarPaper[]>(`/papers/${id}/similar?top_k=8`, []),
  ]);

  const valid = paper.is_valid_for_embedding;

  function previewEmbeddingText(title: string, abstract: string, max = 320): string | null {
    const merged = `${title || ""} ${abstract || ""}`;
    if (!merged.trim()) return null;
    const cleaned = merged
      .replace(/https?:\/\/\S+/gi, " ")
      .replace(/\bdoi\s*:\s*\S+/gi, " ")
      .replace(/\b10\.\d{4,9}\/\S+/g, " ")
      .replace(/©\s*Author\(s\)?\s*\d{4}\.?/gi, " ")
      .replace(/CC\s*Attribution[^.]*\.?/gi, " ")
      .replace(/\s+/g, " ")
      .trim();
    return cleaned.length > max ? `${cleaned.slice(0, max).trimEnd()}…` : cleaned;
  }

  return (
    <div className="space-y-6">
      <PaperChatScope paperId={id} title={paper.title} />
      <header className="space-y-2">
        <Link href="/papers" className="text-xs text-textMuted hover:text-emerald-300">← Volver al explorador</Link>
        <h1 className="text-2xl font-semibold tracking-tight text-balance lg:text-3xl">{paper.title || "Sin título"}</h1>
        <p className="text-sm text-textSubtle">
          {paper.journal || "Journal n/d"} · {paper.year ?? "Año n/d"} · {paper.doc_id || "doc desconocido"}
        </p>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className={valid ? "chip-accent" : "chip-warn"}>
            {valid ? "Indexado en SPECTER2" : "Abstract corto · fuera del índice"}
          </span>
          <span className="chip">abstract de {formatNumber(paper.abstract_char_len)} caracteres</span>
          {paper.doi && (
            <a
              href={`https://doi.org/${paper.doi}`}
              target="_blank"
              rel="noreferrer"
              className="chip hover:border-emerald-500/40 hover:text-emerald-300"
            >
              DOI {paper.doi}
            </a>
          )}
          {paper.pb_result?.top_pb_code && <span className="chip-accent">{paper.pb_result.top_pb_code}</span>}
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <KpiCard
          label="Longitud del abstract"
          value={paper.abstract_char_len}
          helperBadge={valid ? "indexado" : "fuera"}
          helperTone={valid ? "accent" : "warn"}
          helper={valid ? "Supera el criterio de calidad (más de 500 caracteres)." : "No alcanza el mínimo de 500 caracteres tras la limpieza."}
        />
        <KpiCard
          label="Top Planetary Boundary"
          value={paper.pb_result?.top_pb_code || "—"}
          valueFormat="raw"
          helper={
            paper.pb_result
              ? `Confianza ${(paper.pb_result.top_pb_score * 100).toFixed(1)}%`
              : "Sin resultado PB asignado todavía."
          }
        />
      </section>

      <section className="card space-y-3">
        <p className="section-title">Abstract</p>
        <p className="leading-relaxed text-textMain">
          {paper.abstract_norm || "Sin abstract disponible."}
        </p>
        <p className="help-text">El abstract mostrado es la versión normalizada que se utiliza para el embedding.</p>
      </section>

      <AbstractValidationCard
        validation={{
          abstract_detected: paper.abstract_char_len > 0,
          abstract_char_len: paper.abstract_char_len,
          threshold: 500,
          passes_threshold: valid,
          is_valid_for_embedding: valid,
        }}
        embedding={{
          model_id: indexStatus.model_id,
          family: indexStatus.is_specter ? "SPECTER2" : "sentence-transformers",
          is_specter: indexStatus.is_specter,
          embedding_dim: indexStatus.embedding_dim || null,
          embedding_text_rule: indexStatus.embedding_text_rule,
          embedding_text_preview: previewEmbeddingText(paper.title, paper.abstract_norm),
          fallback_used: indexStatus.fallback_used,
        }}
      />

      {paper.pb_result && (
        <section className="card space-y-3">
          <p className="section-title">Resultado Planetary Boundaries</p>
          <h3 className="text-lg font-semibold">
            {paper.pb_result.top_pb_code}
            <span className="ml-2 text-sm font-normal text-textMuted">
              · confianza {(paper.pb_result.top_pb_score * 100).toFixed(1)}%
            </span>
          </h3>
          <p className="text-sm leading-relaxed text-textSubtle">{paper.pb_result.explanation_text || "Sin explicación disponible."}</p>
        </section>
      )}

      <section className="card space-y-4">
        <header className="space-y-1">
          <p className="section-title">Papers similares por contenido</p>
          <h3 className="text-lg font-semibold">Vecinos cercanos sobre el corpus UPV</h3>
          <p className="help-text">
            La similitud se calcula con el embedding {modelLabel(indexStatus.model_id)} del paper (título +
            abstract limpio) frente a los {formatNumber(indexStatus.candidates)} papers indexados del corpus UPV.
          </p>
        </header>
        <SimilarPapersList items={similar} modelLabel={modelLabel(indexStatus.model_id)} />
      </section>

      {comparison && (
        <section className="space-y-4">
          <header>
            <p className="section-title">Comparativa contra el corpus</p>
            <h3 className="text-lg font-semibold">Posición relativa del paper en su PB</h3>
          </header>
          <div className="grid gap-4 lg:grid-cols-2">
            <article className="card space-y-3">
              <p className="section-title">Longitud relativa</p>
              <LengthComparisonChart
                paperLength={comparison.length_comparison.paper_length}
                globalAvg={comparison.length_comparison.global_avg_length}
                pbAvg={comparison.length_comparison.pb_avg_length}
              />
              <p className="help-text">
                El paper se compara contra la media global del corpus y contra la media del mismo PB ({comparison.top_pb_code}).
              </p>
            </article>
            <PaperOverlapCard
              pbCode={comparison.top_pb_code}
              declared={comparison.keyword_comparison.pb_overlap}
              terms={comparison.keyword_comparison.pb_terms_overlap}
              paperKeywords={comparison.keyword_comparison.paper_keywords}
              paperTerms={comparison.keyword_comparison.paper_terms}
              pbTopKeywords={comparison.keyword_comparison.pb_top_keywords}
            />
            <article className="card space-y-3">
              <p className="section-title">Top keywords globales</p>
              <HorizontalKeywordBars data={comparison.keyword_comparison.global_top_keywords} />
            </article>
            <article className="card space-y-3">
              <p className="section-title">Top keywords del PB {comparison.top_pb_code}</p>
              <HorizontalKeywordBars data={comparison.keyword_comparison.pb_top_keywords} />
            </article>
          </div>
        </section>
      )}

      {valid && paper.doc_id ? (
        <section className="card space-y-3">
          <header className="space-y-1">
            <p className="section-title">Mapa 2D del corpus</p>
            <h2 className="text-lg font-semibold">Posición del paper en el espacio SPECTER2</h2>
            <p className="text-xs text-textMuted">
              Proyección UMAP del corpus completo coloreada por Planetary Boundary. El círculo
              blanco con borde verde indica la posición del paper actual; los puntos cercanos
              comparten estructura semántica.
            </p>
          </header>
          <EmbeddingMap highlightDocId={paper.doc_id} sample={6000} height={460} />
        </section>
      ) : null}

      <section className="card space-y-4">
        <KeywordsWithMatches
          title="Keywords declaradas por el autor"
          helper={null}
          words={comparison?.keyword_comparison.paper_keywords || []}
          overlap={comparison?.keyword_comparison.pb_overlap || []}
          pbCode={comparison?.top_pb_code || ""}
          emptyText="No hay keywords estructuradas para este paper."
        />
        <div className="border-t border-line/60 pt-4">
          <KeywordsWithMatches
            title="Términos más frecuentes del abstract"
            helper="Top palabras del paper sin stopwords (precalculado en EDA)."
            words={comparison?.keyword_comparison.paper_terms || []}
            overlap={comparison?.keyword_comparison.pb_terms_overlap || []}
            pbCode={comparison?.top_pb_code || ""}
            emptyText="Sin términos precalculados disponibles."
          />
        </div>
      </section>
    </div>
  );
}
