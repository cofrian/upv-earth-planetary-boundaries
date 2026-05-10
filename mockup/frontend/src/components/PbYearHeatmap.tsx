import { PBYearMatrix } from "@/lib/types";

import { formatNumber } from "./format";

type Props = {
  matrix: PBYearMatrix;
  yearStep?: number;
};

function intensityColor(value: number, max: number): string {
  if (value <= 0 || max <= 0) return "rgba(148, 197, 175, 0.05)";
  const ratio = Math.min(1, value / max);
  const alpha = 0.18 + ratio * 0.7;
  return `rgba(52, 211, 153, ${alpha.toFixed(2)})`;
}

export function PbYearHeatmap({ matrix, yearStep = 2 }: Props) {
  if (!matrix.cells.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface-2 p-6 text-sm text-textMuted">
        No hay datos suficientes para construir la matriz.
      </div>
    );
  }

  const minYear = matrix.years.length ? Math.min(...matrix.years) : 0;
  const maxYear = matrix.years.length ? Math.max(...matrix.years) : 0;
  const visibleYears = matrix.years.filter((y) => y >= 1995 && y <= maxYear);
  const max = Math.max(1, ...matrix.cells.map((c) => c.value));
  const lookup = new Map<string, number>();
  for (const cell of matrix.cells) {
    lookup.set(`${cell.pb_code}::${cell.year}`, cell.value);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-textMuted">
        <span>
          Rango temporal mostrado: {visibleYears[0] ?? "—"} – {maxYear || "—"} (cobertura corpus desde {minYear})
        </span>
        <span>Color = nº papers por celda</span>
      </div>
      <div className="scroll-x">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="sticky left-0 bg-surface-1 px-2 py-1 text-left font-semibold text-textSubtle">PB</th>
              {visibleYears.map((year, idx) => (
                <th
                  key={year}
                  className="px-1 py-1 text-center font-mono text-textMuted"
                  style={{ minWidth: 28 }}
                >
                  {idx % yearStep === 0 ? year : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.pbs.map((pb) => (
              <tr key={pb}>
                <td className="sticky left-0 bg-surface-1 px-2 py-1 font-medium text-textMain whitespace-nowrap">
                  {pb}
                </td>
                {visibleYears.map((year) => {
                  const value = lookup.get(`${pb}::${year}`) ?? 0;
                  return (
                    <td
                      key={`${pb}-${year}`}
                      title={`${pb} · ${year} · ${formatNumber(value)} papers`}
                      className="border border-bg/60 text-center"
                      style={{ background: intensityColor(value, max), minWidth: 28, height: 22 }}
                    >
                      {value > 0 && value >= max * 0.5 ? value : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
