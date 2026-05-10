import { TopicClusterItem } from "@/lib/types";
import { formatNumber, formatPercent } from "./format";

type Props = {
  items: TopicClusterItem[];
};

const PALETTE = ["#34d399", "#22d3ee", "#fbbf24", "#a78bfa", "#f97316", "#f472b6"];

export function TopicClustersCard({ items }: Props) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface-2 p-6 text-sm text-textMuted">
        No hay clusters semánticos precalculados.
      </div>
    );
  }

  const max = Math.max(1, ...items.map((it) => it.n_docs));
  const total = items.reduce((sum, it) => sum + it.n_docs, 0);

  return (
    <div className="space-y-3">
      <div className="grid gap-2">
        {items.map((item, idx) => {
          const pct = (item.n_docs / max) * 100;
          const color = PALETTE[idx % PALETTE.length];
          return (
            <div key={item.cluster_id} className="rounded-xl border border-line bg-surface-2 p-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-textMuted">Cluster {item.cluster_id}</p>
                  <p className="text-sm font-semibold text-textMain">{item.label}</p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="chip">{formatNumber(item.n_docs)} papers</span>
                  <span className="chip-accent">{formatPercent(item.pct_docs)}</span>
                </div>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-surface-3">
                <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>
      <p className="help-text">
        Topics descubiertos automáticamente sobre el corpus que pasa filtros (KMeans sobre embeddings semánticos).
        Total {formatNumber(total)} papers agrupados en {items.length} clusters.
      </p>
    </div>
  );
}
