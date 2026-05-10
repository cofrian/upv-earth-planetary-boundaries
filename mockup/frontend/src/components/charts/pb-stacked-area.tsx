"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PBYearMatrix } from "@/lib/types";

const PB_COLORS: Record<string, string> = {
  "1 - Climate Change": "#dc2626",
  "2 - Ocean Acidification": "#0891b2",
  "3 - Stratospheric Ozone Depletion": "#2563eb",
  "4 - Biogeochemical Flows": "#f97316",
  "5 - Global Freshwater Use": "#06b6d4",
  "6 - Land System Change": "#16a34a",
  "7 - Biosphere Integrity": "#84cc16",
  "8 - Novel Entities": "#a855f7",
  "9 - Atmospheric Aerosol Loading": "#fbbf24",
};

const FALLBACK_COLOR = "#94a3b8";

const AreaChartAny = AreaChart as any;
const AreaAny = Area as any;
const CartesianGridAny = CartesianGrid as any;
const XAxisAny = XAxis as any;
const YAxisAny = YAxis as any;
const TooltipAny = Tooltip as any;
const LegendAny = Legend as any;

const AXIS_TICK = { fill: "#a9c5b7", fontSize: 11 };
const GRID_STROKE = "rgba(46, 92, 73, 0.4)";
const TOOLTIP_STYLE = {
  background: "rgba(7, 16, 12, 0.96)",
  border: "1px solid rgba(52, 211, 153, 0.35)",
  borderRadius: "10px",
  padding: "10px 12px",
  boxShadow: "0 12px 32px rgba(2, 8, 6, 0.6)",
  color: "#e6f4ed",
  fontSize: "12px",
  lineHeight: "1.45",
};
const TOOLTIP_LABEL = { color: "#a9c5b7", fontWeight: 500, marginBottom: "4px" };
const TOOLTIP_ITEM = { color: "#e6f4ed" };

interface Props {
  data: PBYearMatrix;
  /** Año mínimo a mostrar (descarta colas largas vacías). Default 1990. */
  minYear?: number;
  height?: number;
}

export function PBStackedAreaChart({ data, minYear = 1990, height = 360 }: Props) {
  const { rows, pbs } = useMemo(() => {
    if (!data?.years?.length || !data.pbs?.length) {
      return { rows: [], pbs: [] as string[] };
    }
    const pbsSorted = [...data.pbs].sort();
    const yearsFiltered = data.years.filter((y) => y >= minYear).sort((a, b) => a - b);
    const cellMap = new Map<string, number>();
    for (const cell of data.cells) {
      cellMap.set(`${cell.pb_code}__${cell.year}`, cell.value);
    }
    const rowsBuilt = yearsFiltered.map((year) => {
      const row: Record<string, number | string> = { year };
      let total = 0;
      for (const pb of pbsSorted) {
        const v = cellMap.get(`${pb}__${year}`) || 0;
        row[pb] = v;
        total += v;
      }
      row.__total = total;
      return row;
    });
    return { rows: rowsBuilt, pbs: pbsSorted };
  }, [data, minYear]);

  if (!rows.length) {
    return (
      <p className="text-sm text-textMuted">
        No hay datos temporales por Planetary Boundary disponibles.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChartAny data={rows} margin={{ top: 14, right: 24, left: 0, bottom: 28 }}>
        <CartesianGridAny strokeDasharray="3 6" stroke={GRID_STROKE} vertical={false} />
        <XAxisAny dataKey="year" stroke="#a9c5b7" tick={AXIS_TICK} tickMargin={8} />
        <YAxisAny stroke="#a9c5b7" tick={AXIS_TICK} tickMargin={4} />
        <TooltipAny
          contentStyle={TOOLTIP_STYLE}
          labelStyle={TOOLTIP_LABEL}
          itemStyle={TOOLTIP_ITEM}
          cursor={{ stroke: "rgba(52, 211, 153, 0.25)", strokeWidth: 1 }}
        />
        <LegendAny
          iconType="square"
          wrapperStyle={{ fontSize: 11, color: "#a9c5b7", paddingTop: 6 }}
        />
        {pbs.map((pb) => (
          <AreaAny
            key={pb}
            type="monotone"
            dataKey={pb}
            stackId="pb"
            stroke={PB_COLORS[pb] || FALLBACK_COLOR}
            fill={PB_COLORS[pb] || FALLBACK_COLOR}
            fillOpacity={0.78}
            strokeWidth={1}
            isAnimationActive={false}
          />
        ))}
      </AreaChartAny>
    </ResponsiveContainer>
  );
}

export function PBLineChart({ data, minYear = 1990, height = 320 }: Props) {
  const { rows, pbs } = useMemo(() => {
    if (!data?.years?.length || !data.pbs?.length) {
      return { rows: [], pbs: [] as string[] };
    }
    const pbsSorted = [...data.pbs].sort();
    const yearsFiltered = data.years.filter((y) => y >= minYear).sort((a, b) => a - b);
    const cellMap = new Map<string, number>();
    for (const cell of data.cells) cellMap.set(`${cell.pb_code}__${cell.year}`, cell.value);
    const rowsBuilt = yearsFiltered.map((year) => {
      const row: Record<string, number | string> = { year };
      for (const pb of pbsSorted) row[pb] = cellMap.get(`${pb}__${year}`) || 0;
      return row;
    });
    return { rows: rowsBuilt, pbs: pbsSorted };
  }, [data, minYear]);

  if (!rows.length) return null;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChartAny data={rows} margin={{ top: 14, right: 24, left: 0, bottom: 28 }}>
        <CartesianGridAny strokeDasharray="3 6" stroke={GRID_STROKE} vertical={false} />
        <XAxisAny dataKey="year" stroke="#a9c5b7" tick={AXIS_TICK} />
        <YAxisAny stroke="#a9c5b7" tick={AXIS_TICK} />
        <TooltipAny
          contentStyle={TOOLTIP_STYLE}
          labelStyle={TOOLTIP_LABEL}
          itemStyle={TOOLTIP_ITEM}
        />
        <LegendAny iconType="line" wrapperStyle={{ fontSize: 11, color: "#a9c5b7" }} />
        {pbs.map((pb) => (
          <AreaAny
            key={pb}
            type="monotone"
            dataKey={pb}
            stroke={PB_COLORS[pb] || FALLBACK_COLOR}
            fill={PB_COLORS[pb] || FALLBACK_COLOR}
            fillOpacity={0.0}
            strokeWidth={2}
            isAnimationActive={false}
          />
        ))}
      </AreaChartAny>
    </ResponsiveContainer>
  );
}

export { PB_COLORS };
