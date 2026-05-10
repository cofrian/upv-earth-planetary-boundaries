import { PBSimilarityMatrix, PBSimilarityPair } from "@/lib/types";

type Props = {
  matrix: PBSimilarityMatrix;
  topPairs: PBSimilarityPair[];
};

function intensityColor(value: number): string {
  if (!Number.isFinite(value)) return "rgba(148, 197, 175, 0.05)";
  const clamped = Math.max(0, Math.min(1, value));
  const alpha = 0.12 + clamped * 0.78;
  return `rgba(52, 211, 153, ${alpha.toFixed(2)})`;
}

function shortPb(label: string): string {
  const match = label.match(/^(\d+)/);
  if (match) return `PB${match[1]}`;
  return label.slice(0, 3);
}

export function PbSimilarityHeatmap({ matrix, topPairs }: Props) {
  if (!matrix.cells.length || !matrix.pbs.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface-2 p-6 text-sm text-textMuted">
        No hay matriz de similitud precalculada para esta métrica.
      </div>
    );
  }

  const lookup = new Map<string, number>();
  for (const cell of matrix.cells) {
    lookup.set(`${cell.pb_a}::${cell.pb_b}`, cell.value);
  }

  return (
    <div className="space-y-4">
      <div className="scroll-x">
        <table className="w-full border-separate border-spacing-0 text-xs">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-surface-1 px-2 py-1 text-left text-textMuted">
                <span className="text-[10px] uppercase tracking-widest">PB</span>
              </th>
              {matrix.pbs.map((pb) => (
                <th
                  key={pb}
                  title={pb}
                  className="px-1 py-1 text-center font-mono text-textMuted"
                  style={{ minWidth: 44 }}
                >
                  {shortPb(pb)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.pbs.map((pbA) => (
              <tr key={pbA}>
                <td
                  className="sticky left-0 z-10 bg-surface-1 px-2 py-1 text-textMain whitespace-nowrap"
                  title={pbA}
                >
                  <span className="font-medium">{shortPb(pbA)}</span>
                  <span className="ml-1 hidden text-textMuted xl:inline">{pbA.replace(/^\d+\s*-\s*/, "")}</span>
                </td>
                {matrix.pbs.map((pbB) => {
                  const value = lookup.get(`${pbA}::${pbB}`) ?? 0;
                  const isDiag = pbA === pbB;
                  return (
                    <td
                      key={`${pbA}-${pbB}`}
                      title={`${pbA} ↔ ${pbB} · similitud ${value.toFixed(3)}`}
                      className="border border-bg/60 text-center align-middle"
                      style={{
                        background: isDiag ? "rgba(52,211,153,0.18)" : intensityColor(value),
                        minWidth: 44,
                        height: 32,
                      }}
                    >
                      <span className={`font-mono ${value >= 0.7 ? "text-emerald-200" : "text-textMain/80"}`}>
                        {isDiag ? "—" : value.toFixed(2)}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {topPairs.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-textMuted">
            Top {topPairs.length} pares con mayor similitud
          </p>
          <ul className="mt-2 grid gap-2 md:grid-cols-2">
            {topPairs.map((pair) => (
              <li
                key={`${pair.pb_a}-${pair.pb_b}`}
                className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm"
              >
                <span className="text-textMain">
                  <span className="font-mono text-emerald-300">{shortPb(pair.pb_a)}</span> ↔{" "}
                  <span className="font-mono text-emerald-300">{shortPb(pair.pb_b)}</span>{" "}
                  <span className="text-textSubtle">
                    ({pair.pb_a.replace(/^\d+\s*-\s*/, "")} ↔ {pair.pb_b.replace(/^\d+\s*-\s*/, "")})
                  </span>
                </span>
                <span className="font-mono text-textMain">{(pair.similarity * 100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
