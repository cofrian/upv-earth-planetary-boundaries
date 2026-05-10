import { PBComplexityItem } from "@/lib/types";
import { formatNumber } from "./format";

type Props = {
  items: PBComplexityItem[];
};

function shortPb(label: string): string {
  return label.replace(/^(\d+)\s*-\s*/, "$1 · ");
}

export function AbstractComplexityTable({ items }: Props) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface-2 p-6 text-sm text-textMuted">
        No hay estadísticas disponibles para este bloque.
      </div>
    );
  }

  const max = Math.max(1, ...items.map((it) => it.mean));

  return (
    <div className="space-y-3">
      <div className="scroll-x">
        <table className="table-pro">
          <thead>
            <tr>
              <th>PB</th>
              <th className="text-right">Papers</th>
              <th className="text-right">Media</th>
              <th className="text-right">Mediana</th>
              <th className="text-right">σ</th>
              <th className="text-right">Min</th>
              <th className="text-right">Max</th>
              <th>Distribución relativa de la media</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const pct = (item.mean / max) * 100;
              return (
                <tr key={item.pb_code}>
                  <td className="text-textMain">{shortPb(item.pb_code)}</td>
                  <td className="text-right tabular-nums text-textSubtle">{formatNumber(item.count)}</td>
                  <td className="text-right tabular-nums text-textMain">{formatNumber(item.mean, 0)}</td>
                  <td className="text-right tabular-nums text-textSubtle">{formatNumber(item.median, 0)}</td>
                  <td className="text-right tabular-nums text-textSubtle">{formatNumber(item.std, 0)}</td>
                  <td className="text-right tabular-nums text-textMuted">{formatNumber(item.min, 0)}</td>
                  <td className="text-right tabular-nums text-textMuted">{formatNumber(item.max, 0)}</td>
                  <td className="min-w-[180px]">
                    <div className="h-2 rounded-full bg-surface-3">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${Math.max(4, pct)}%`,
                          background: "linear-gradient(90deg,#34d399,#10b981)",
                        }}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="help-text">
        Longitud del abstract limpio en palabras (no caracteres). Los PBs con mayor desviación típica son los más
        heterogéneos en cuanto a densidad textual.
      </p>
    </div>
  );
}
