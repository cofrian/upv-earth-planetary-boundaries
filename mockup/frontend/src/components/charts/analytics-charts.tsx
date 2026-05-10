"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const BAR_COLORS = [
  "#34d399",
  "#10b981",
  "#22d3ee",
  "#fbbf24",
  "#a78bfa",
  "#f97316",
  "#f472b6",
  "#94a3b8",
  "#fb7185",
  "#84cc16",
];

const PIE_COLORS = [
  "#34d399",
  "#22d3ee",
  "#fbbf24",
  "#a78bfa",
  "#f97316",
  "#f472b6",
  "#94a3b8",
  "#fb7185",
  "#84cc16",
  "#10b981",
];

const AXIS_TICK = { fill: "#a9c5b7", fontSize: 11 };
const GRID_STROKE = "rgba(46, 92, 73, 0.45)";
const TOOLTIP_WRAPPER = { outline: "none", zIndex: 30 } as const;
const TOOLTIP_STYLE = {
  background: "rgba(7, 16, 12, 0.96)",
  border: "1px solid rgba(52, 211, 153, 0.35)",
  borderRadius: "10px",
  padding: "8px 12px",
  boxShadow: "0 12px 32px rgba(2, 8, 6, 0.6)",
  color: "#e6f4ed",
  fontSize: "12px",
  lineHeight: "1.45",
};
const TOOLTIP_LABEL = { color: "#a9c5b7", fontWeight: 500, marginBottom: "2px" };
const TOOLTIP_ITEM = { color: "#e6f4ed" };

const AreaChartAny = AreaChart as any;
const BarChartAny = BarChart as any;
const LineChartAny = LineChart as any;
const PieChartAny = PieChart as any;
const CartesianGridAny = CartesianGrid as any;
const XAxisAny = XAxis as any;
const YAxisAny = YAxis as any;
const TooltipAny = Tooltip as any;
const BarAny = Bar as any;
const LineAny = Line as any;
const AreaAny = Area as any;
const PieAny = Pie as any;
const CellAny = Cell as any;
const LegendAny = Legend as any;

type Pair = {
  label: string;
  value: number;
};

type KeywordPair = {
  keyword: string;
  value: number;
};

type TemporalPair = {
  year: number;
  valid: number;
  for_embeddings: number;
};

function hasData<T extends { value?: number }>(data: T[]): boolean {
  if (!data?.length) return false;
  return data.some((item) => (typeof item.value === "number" ? item.value > 0 : true));
}

function shortLabel(label: string, max = 18): string {
  if (!label) return "";
  if (label.length <= max) return label;
  return `${label.slice(0, max - 1)}...`;
}

const empty = (
  <div className="grid h-72 w-full place-items-center text-sm text-textMuted">No hay datos para mostrar</div>
);

export function DistBarChart({ data }: { data: Pair[] }) {
  if (!hasData(data)) return empty;

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
                <BarChartAny data={data} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
                    <CartesianGridAny strokeDasharray="3 3" stroke={GRID_STROKE} />
                    <XAxisAny
            dataKey="label"
            angle={-30}
            textAnchor="end"
            interval={0}
            tick={AXIS_TICK}
            minTickGap={8}
            tickFormatter={(value: string) => shortLabel(value)}
          />
                    <YAxisAny tick={AXIS_TICK} width={42} />
                    <TooltipAny
            wrapperStyle={TOOLTIP_WRAPPER}
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL}
            itemStyle={TOOLTIP_ITEM}
            cursor={{ fill: "rgba(52,211,153,0.08)" }}
            formatter={(value: number, _name: string, entry: { payload?: Pair }) => [value, entry?.payload?.label || "valor"]}
          />
                    <BarAny dataKey="value" radius={[8, 8, 0, 0]}>
            {data.map((entry, index) => (
                            <CellAny key={`${entry.label}-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
            ))}
          </BarAny>
        </BarChartAny>
      </ResponsiveContainer>
    </div>
  );
}

export function DistLineChart({ data }: { data: Pair[] }) {
  if (!hasData(data)) return empty;

  const isYearSeries = data.every((item) => /^\d{4}$/.test(item.label));
  const xTickInterval = isYearSeries ? Math.max(0, Math.ceil(data.length / 12) - 1) : "preserveStartEnd";
  const showDots = data.length <= 24;

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
                <LineChartAny data={data} margin={{ top: 12, right: 12, left: 0, bottom: isYearSeries ? 32 : 16 }}>
                    <CartesianGridAny strokeDasharray="3 3" stroke={GRID_STROKE} />
                    <XAxisAny
            dataKey="label"
            tick={AXIS_TICK}
            interval={xTickInterval}
            angle={isYearSeries ? -30 : 0}
            textAnchor={isYearSeries ? "end" : "middle"}
            minTickGap={isYearSeries ? 10 : 8}
            tickFormatter={(value: string) => shortLabel(value, 10)}
          />
                    <YAxisAny tick={AXIS_TICK} width={42} />
                    <TooltipAny
            wrapperStyle={TOOLTIP_WRAPPER}
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL}
            itemStyle={TOOLTIP_ITEM}
            cursor={{ stroke: "rgba(52,211,153,0.25)" }}
          />
                    <LineAny
            type="monotone"
            dataKey="value"
            stroke="#34d399"
            strokeWidth={2.5}
            dot={showDots ? { r: 2.5, fill: "#34d399" } : false}
            activeDot={{ r: 4, fill: "#34d399" }}
          />
        </LineChartAny>
      </ResponsiveContainer>
    </div>
  );
}

export function DistPieChart({ data }: { data: Pair[] }) {
  if (!hasData(data)) return empty;

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
                <PieChartAny>
                    <TooltipAny wrapperStyle={TOOLTIP_WRAPPER} contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL} itemStyle={TOOLTIP_ITEM} />
                    <LegendAny
            wrapperStyle={{ fontSize: 12, color: "#a9c5b7" }}
            formatter={(value: string) => shortLabel(value, 22)}
          />
                    <PieAny data={data} dataKey="value" nameKey="label" innerRadius={56} outerRadius={96} paddingAngle={2} minAngle={2}>
            {data.map((entry, index) => (
                            <CellAny key={`${entry.label}-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </PieAny>
        </PieChartAny>
      </ResponsiveContainer>
    </div>
  );
}

export function KeywordBars({ data }: { data: KeywordPair[] }) {
  const chartData = data.map((item) => ({ label: item.keyword, value: item.value }));
  return <DistBarChart data={chartData} />;
}

export function LengthComparisonChart({
  paperLength,
  globalAvg,
  pbAvg,
}: {
  paperLength: number;
  globalAvg: number;
  pbAvg: number;
}) {
  const data = [
    { label: "Paper", value: paperLength },
    { label: "Media global", value: Math.round(globalAvg) },
    { label: "Media mismo PB", value: Math.round(pbAvg) },
  ];
  return <DistBarChart data={data} />;
}

export function TemporalQualityChart({ data }: { data: TemporalPair[] }) {
  if (!data?.length) return empty;
  const chartData = data.map((item) => ({
    label: String(item.year),
    valid: item.valid,
    for_embeddings: item.for_embeddings,
  }));

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer>
                <AreaChartAny data={chartData} margin={{ top: 14, right: 16, left: 0, bottom: 30 }}>
          <defs>
            <linearGradient id="validGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="embGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#34d399" stopOpacity={0.65} />
              <stop offset="95%" stopColor="#34d399" stopOpacity={0.06} />
            </linearGradient>
          </defs>
                    <CartesianGridAny strokeDasharray="3 3" stroke={GRID_STROKE} />
                    <XAxisAny dataKey="label" tick={AXIS_TICK} angle={-30} textAnchor="end" minTickGap={10} />
                    <YAxisAny tick={AXIS_TICK} width={42} />
                    <TooltipAny wrapperStyle={TOOLTIP_WRAPPER} contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL} itemStyle={TOOLTIP_ITEM} />
                    <LegendAny wrapperStyle={{ fontSize: 12, color: "#a9c5b7" }} />
                    <AreaAny
            type="monotone"
            dataKey="valid"
            name="Corpus válido"
            stroke="#10b981"
            fill="url(#validGradient)"
            strokeWidth={2}
          />
                    <AreaAny
            type="monotone"
            dataKey="for_embeddings"
            name="Apto para embeddings"
            stroke="#34d399"
            fill="url(#embGradient)"
            strokeWidth={2.5}
          />
        </AreaChartAny>
      </ResponsiveContainer>
    </div>
  );
}

export function HorizontalKeywordBars({ data }: { data: KeywordPair[] }) {
  if (!data?.length) return empty;
  const max = Math.max(1, ...data.map((item) => item.value));
  return (
    <ul className="space-y-1.5">
      {data.map((item) => {
        const pct = (item.value / max) * 100;
        return (
          <li key={item.keyword} className="flex items-center gap-3 text-xs text-textSubtle">
            <span className="w-32 truncate font-medium text-textMain" title={item.keyword}>
              {item.keyword}
            </span>
            <div className="flex-1 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-2.5 rounded-full bg-emerald-500/70"
                style={{ width: `${pct}%`, background: "linear-gradient(90deg,#34d399,#10b981)" }}
              />
            </div>
            <span className="w-10 text-right font-mono text-textMain">{item.value}</span>
          </li>
        );
      })}
    </ul>
  );
}
