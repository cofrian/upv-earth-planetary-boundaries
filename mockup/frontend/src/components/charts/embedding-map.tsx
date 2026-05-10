"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { apiGet } from "@/lib/api";
import type { EmbeddingMapPoint, EmbeddingMapResponse } from "@/lib/types";

import { PB_COLORS } from "./pb-stacked-area";

const FALLBACK_COLOR = "#94a3b8";

const ScatterChartAny = ScatterChart as any;
const ScatterAny = Scatter as any;
const CartesianGridAny = CartesianGrid as any;
const XAxisAny = XAxis as any;
const YAxisAny = YAxis as any;
const ZAxisAny = ZAxis as any;
const TooltipAny = Tooltip as any;

const TOOLTIP_STYLE = {
  background: "rgba(7, 16, 12, 0.96)",
  border: "1px solid rgba(52, 211, 153, 0.35)",
  borderRadius: "10px",
  padding: "10px 12px",
  boxShadow: "0 12px 32px rgba(2, 8, 6, 0.6)",
  color: "#e6f4ed",
  fontSize: "12px",
  lineHeight: "1.45",
  maxWidth: "320px",
};

interface Props {
  /** doc_id del paper a destacar (opcional). */
  highlightDocId?: string | null;
  /** Punto extra a dibujar (paper subido / pre-recuperado externamente). */
  highlightPoint?: EmbeddingMapPoint | null;
  /** Tamaño máximo de muestreo enviado al backend. */
  sample?: number;
  height?: number;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: any }) {
  if (!active || !payload?.length) return null;
  const p: EmbeddingMapPoint = payload[0]?.payload;
  if (!p) return null;
  const isHighlighted = (p as any).__highlight;
  return (
    <div style={TOOLTIP_STYLE}>
      <div style={{ color: "#a9c5b7", marginBottom: 4, fontWeight: 500 }}>
        {isHighlighted ? "Paper analizado" : "Paper del corpus"}
      </div>
      {p.title ? (
        <div style={{ fontWeight: 600, color: "#e6f4ed" }}>{p.title.slice(0, 160)}</div>
      ) : (
        <div style={{ fontStyle: "italic", color: "#a9c5b7" }}>(título no disponible)</div>
      )}
      <div style={{ color: "#a9c5b7", marginTop: 4 }}>
        PB: <span style={{ color: "#e6f4ed" }}>{p.pb_code || "—"}</span>
        {typeof p.year === "number" ? ` · ${p.year}` : ""}
      </div>
    </div>
  );
}

export function EmbeddingMap({
  highlightDocId,
  highlightPoint,
  sample = 6000,
  height = 460,
}: Props) {
  const [data, setData] = useState<EmbeddingMapResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<EmbeddingMapResponse>(`/analytics/embedding-map?sample=${sample}`)
      .then((d) => {
        if (cancelled) return;
        setData(d);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sample]);

  const groups = useMemo(() => {
    if (!data?.points?.length) return [] as { pb: string; color: string; points: EmbeddingMapPoint[] }[];
    const byPB = new Map<string, EmbeddingMapPoint[]>();
    for (const p of data.points) {
      const key = p.pb_code || "Sin PB";
      if (!byPB.has(key)) byPB.set(key, []);
      byPB.get(key)!.push(p);
    }
    return Array.from(byPB.entries())
      .map(([pb, points]) => ({
        pb,
        color: PB_COLORS[pb] || FALLBACK_COLOR,
        points,
      }))
      .sort((a, b) => a.pb.localeCompare(b.pb));
  }, [data]);

  // Punto a destacar: prioriza el punto pasado por prop, si no hay
  // busca por doc_id en el dataset cargado.
  const highlight = useMemo<EmbeddingMapPoint | null>(() => {
    if (highlightPoint) return { ...highlightPoint, __highlight: true } as any;
    if (!highlightDocId || !data?.points) return null;
    const found = data.points.find((p) => p.doc_id === highlightDocId);
    return found ? ({ ...found, __highlight: true } as any) : null;
  }, [data, highlightDocId, highlightPoint]);

  if (loading) {
    return (
      <div className="card-tight skeleton" style={{ height }} aria-label="Cargando mapa 2D" />
    );
  }
  if (error) {
    return (
      <p className="text-sm text-rose">No se pudo cargar el mapa 2D: {error}</p>
    );
  }
  if (!data?.available || !data.points.length) {
    return (
      <p className="text-sm text-textMuted">
        Mapa 2D no disponible. Ejecuta <code>scripts/precompute_2d_projection</code>.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        {groups.map((g) => (
          <span
            key={g.pb}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2 py-1 text-textSubtle"
          >
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: g.color }}
            />
            <span className="font-mono">{g.pb}</span>
            <span className="text-textMuted">·</span>
            <span>{g.points.length}</span>
          </span>
        ))}
        {highlight ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-line-accent bg-emerald-500/10 px-2 py-1 text-emerald-300">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-white ring-2 ring-emerald-300" />
            Paper analizado
          </span>
        ) : null}
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChartAny margin={{ top: 8, right: 12, left: 0, bottom: 12 }}>
          <CartesianGridAny strokeDasharray="2 6" stroke="rgba(46, 92, 73, 0.25)" />
          <XAxisAny
            type="number"
            dataKey="x"
            domain={["dataMin - 1", "dataMax + 1"]}
            tick={false}
            stroke="rgba(255,255,255,0.05)"
          />
          <YAxisAny
            type="number"
            dataKey="y"
            domain={["dataMin - 1", "dataMax + 1"]}
            tick={false}
            stroke="rgba(255,255,255,0.05)"
          />
          <ZAxisAny range={[24, 24]} />
          <TooltipAny
            content={<CustomTooltip />}
            cursor={{ stroke: "rgba(52, 211, 153, 0.25)", strokeWidth: 1 }}
          />
          {groups.map((g) => (
            <ScatterAny
              key={g.pb}
              data={g.points}
              fill={g.color}
              fillOpacity={0.55}
              stroke="none"
              isAnimationActive={false}
              shape="circle"
            />
          ))}
          {highlight ? (
            <ScatterAny
              data={[highlight]}
              fill="#ffffff"
              stroke="#34d399"
              strokeWidth={2.5}
              isAnimationActive={false}
              shape="circle"
              zAxisId={0}
              z={120 as any}
            />
          ) : null}
        </ScatterChartAny>
      </ResponsiveContainer>
      <p className="help-text">
        Proyección UMAP 2D · cosine · {data.total.toLocaleString("es-ES")} papers indexados
        ({data.returned.toLocaleString("es-ES")} mostrados).
        Cada punto es un paper coloreado por su Planetary Boundary principal según la
        clasificación SPECTER2. La cercanía espacial implica similitud semántica
        (no temporal ni temática literal).
      </p>
    </div>
  );
}
