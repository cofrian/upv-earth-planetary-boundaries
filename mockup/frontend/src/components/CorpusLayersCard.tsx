import { CorpusKPIs } from "@/lib/types";
import { formatNumber, formatPercent } from "./format";

type Props = {
  data: CorpusKPIs;
};

const layers = [
  {
    key: "total_raw" as const,
    label: "Corpus bruto",
    description: "PDFs / papers procesados sin filtros aplicados.",
    badge: "bruto",
  },
  {
    key: "with_abstract" as const,
    label: "Con abstract detectado",
    description: "Papers con algún abstract identificable tras parsing.",
    badge: "con abstract",
  },
  {
    key: "valid" as const,
    label: "Pasa filtros del pipeline",
    description: "Idioma, dedupe y abstract original suficiente.",
    badge: "filtros básicos",
  },
  {
    key: "for_embeddings" as const,
    label: "Corpus válido SPECTER2",
    description: "Abstract limpio con más de 500 caracteres tras la normalización.",
    badge: "abstract > 500",
  },
  {
    key: "indexed" as const,
    label: "Indexado en SPECTER2",
    description: "Embedding generado y disponible para similitud.",
    badge: "indexado",
  },
];

export function CorpusLayersCard({ data }: Props) {
  const max = data.total_raw || 1;

  return (
    <section className="card space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <p className="section-title">Capas del corpus UPV</p>
          <h3 className="text-lg font-semibold text-textMain">
            De {formatNumber(data.total_raw)} papers brutos a{" "}
            <span className="text-emerald-400">{formatNumber(data.indexed)}</span> indexados en SPECTER2
          </h3>
          <p className="text-xs text-textMuted">
            El corpus válido del producto es la capa <span className="text-emerald-300">SPECTER2</span>; las
            anteriores son etapas intermedias del pipeline.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip">filtros {formatPercent(data.valid_pct)}</span>
          <span className="chip-accent">SPECTER2 {formatPercent(data.embedding_pct)}</span>
        </div>
      </header>

      <ol className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {layers.map((layer, idx) => {
          const value = data[layer.key];
          const pct = (value / max) * 100;
          const isHighlight = layer.key === "for_embeddings";
          return (
            <li
              key={layer.key}
              className={`relative flex flex-col justify-between rounded-2xl border bg-surface-2 p-4 transition ${
                isHighlight
                  ? "border-emerald-500/50 bg-gradient-to-br from-emerald-500/10 to-transparent"
                  : "border-line hover:border-emerald-500/40"
              }`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-300">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span className="chip">{layer.badge}</span>
              </div>
              <div className="mt-2 space-y-1">
                <p className="text-sm font-semibold text-textMain leading-tight">{layer.label}</p>
                <p className="text-[11px] leading-snug text-textMuted">{layer.description}</p>
              </div>
              <div className="mt-3 flex items-baseline justify-between gap-2">
                <span className={`text-2xl font-semibold tabular-nums ${isHighlight ? "text-emerald-300" : "text-textMain"}`}>
                  {formatNumber(value)}
                </span>
                <span className="font-mono text-xs text-textMuted">{pct.toFixed(1)}%</span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.max(2, pct)}%`,
                    background: "linear-gradient(90deg,#34d399,#10b981)",
                  }}
                />
              </div>
            </li>
          );
        })}
      </ol>

      <footer className="space-y-2 text-xs text-textMuted">
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip">criterio: abstract limpio &gt; 500 caracteres</span>
          <span className="chip">representación: título + abstract limpio</span>
          <span className="chip">cobertura del índice {formatPercent(data.embedding_pct_of_valid)}</span>
        </div>
        {data.valid > data.for_embeddings && (
          <p className="leading-relaxed">
            <span className="text-textSubtle">
              {formatNumber(data.valid - data.for_embeddings)} papers
            </span>{" "}
            pasan los filtros básicos del pipeline pero, tras la limpieza semántica, su abstract baja por
            debajo de 500 caracteres y por tanto no entran al corpus SPECTER2 ni al índice de similitud.
          </p>
        )}
      </footer>
    </section>
  );
}
