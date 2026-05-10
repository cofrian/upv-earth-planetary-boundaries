import { EmbeddingCoverage, IndexStatus } from "@/lib/types";
import { formatNumber, formatPercent, modelLabel } from "./format";

type Props = {
  coverage: EmbeddingCoverage;
  index: IndexStatus;
};

export function CorpusQualityPanel({ coverage, index }: Props) {
  const stats = coverage.embedding_text_length_stats;
  const tokens = coverage.approx_token_buckets || [];

  return (
    <section className="card space-y-5">
      <header className="space-y-1">
        <p className="section-title">Calidad del corpus para embeddings</p>
        <h3 className="text-lg font-semibold text-textMain">
          Cobertura SPECTER2 sobre <span className="text-emerald-400">{formatNumber(coverage.valid_total)}</span>{" "}
          papers válidos
        </h3>
        <p className="help-text">
          El criterio de calidad exige que el abstract limpio supere 500 caracteres. Aplicarlo sobre el texto
          limpio (no sobre el abstract original) es más estricto: descarta papers cuyo contenido útil queda
          reducido a cabeceras editoriales, paginación o metadatos de revista.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">Aptos para embeddings</span>
          <span className="stat-value">{formatNumber(coverage.embedding_total)}</span>
          <span className="text-xs text-textMuted">de {formatNumber(coverage.valid_total)} válidos</span>
        </div>
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">Descartes por abstract corto</span>
          <span className="stat-value">{formatNumber(coverage.discarded_short_abstract)}</span>
          <span className="text-xs text-textMuted">menos de 500 caracteres tras limpieza</span>
        </div>
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">Long. media texto embedding</span>
          <span className="stat-value">{formatNumber(stats.mean, 0)}</span>
          <span className="text-xs text-textMuted">mediana {formatNumber(stats.median, 0)} · p90 {formatNumber(stats.p90, 0)}</span>
        </div>
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">Cobertura sobre válido</span>
          <span className="stat-value">{formatPercent(coverage.coverage_vs_valid_pct)}</span>
          <span className="text-xs text-textMuted">índice FAISS preparado</span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-textMuted">Modelo activo</p>
          <p className="mt-1 text-sm font-semibold text-textMain">{modelLabel(index.model_id)}</p>
          <p className="text-xs text-textMuted">Embeddings de papers científicos · representación contextual</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div className="rounded-lg border border-line bg-surface-1 p-2">
              <p className="text-[10px] uppercase tracking-widest text-textMuted">Dimensión</p>
              <p className="font-semibold text-textMain">{index.embedding_dim || "—"}</p>
            </div>
            <div className="rounded-lg border border-line bg-surface-1 p-2">
              <p className="text-[10px] uppercase tracking-widest text-textMuted">Candidatos</p>
              <p className="font-semibold text-textMain">{formatNumber(index.candidates)}</p>
            </div>
            <div className="rounded-lg border border-line bg-surface-1 p-2">
              <p className="text-[10px] uppercase tracking-widest text-textMuted">Indexados</p>
              <p className="font-semibold text-textMain">{formatNumber(index.vectors)}</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
            <span className={index.is_specter ? "chip-accent" : "chip-warn"}>
              {index.is_specter ? "SPECTER2" : "Modelo alternativo"}
            </span>
            <span className={index.is_precomputed ? "chip-accent" : "chip-warn"}>
              {index.is_precomputed ? "embeddings precalculados" : "cálculo en caliente"}
            </span>
            <span className={index.is_built ? "chip-accent" : "chip"}>
              {index.is_built ? "índice listo" : "índice diferido"}
            </span>
            {index.fallback_used && <span className="chip-warn">modelo alternativo</span>}
          </div>
        </div>

        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-textMuted">Distribución aproximada de tokens</p>
          <p className="mt-1 text-sm text-textSubtle">
            Estimado dividiendo la longitud del texto entre 4 caracteres por token.
          </p>
          <ul className="mt-3 space-y-1.5">
            {tokens.map((bucket) => {
              const max = Math.max(1, ...tokens.map((b) => b.value));
              const pct = (bucket.value / max) * 100;
              return (
                <li key={bucket.label} className="flex items-center gap-3 text-xs text-textSubtle">
                  <span className="w-16 font-mono text-textMuted">{bucket.label}</span>
                  <div className="flex-1 overflow-hidden rounded-full bg-surface-1">
                    <div className="h-2 rounded-full bg-emerald-500/70" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-10 text-right font-mono text-textMain">{bucket.value}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
