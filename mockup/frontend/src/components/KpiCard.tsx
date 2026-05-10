import { ReactNode } from "react";

import { formatCompact, formatNumber, formatPercent } from "./format";

type Props = {
  label: string;
  value: number | string;
  helper?: string;
  helperBadge?: string;
  helperTone?: "neutral" | "accent" | "warn";
  valueFormat?: "number" | "compact" | "percent" | "raw";
  digits?: number;
  icon?: ReactNode;
  highlight?: boolean;
};

export function KpiCard({
  label,
  value,
  helper,
  helperBadge,
  helperTone = "neutral",
  valueFormat = "number",
  digits = 0,
  icon,
  highlight,
}: Props) {
  const renderedValue = (() => {
    if (typeof value === "string") return value;
    if (valueFormat === "compact") return formatCompact(value);
    if (valueFormat === "percent") return formatPercent(value, digits);
    if (valueFormat === "raw") return String(value);
    return formatNumber(value, digits);
  })();

  const badgeClass =
    helperTone === "accent"
      ? "chip-accent"
      : helperTone === "warn"
      ? "chip-warn"
      : "chip";

  return (
    <article className={`kpi-card ${highlight ? "ring-emerald-soft" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="section-title">{label}</p>
        {icon && <span className="text-emerald-400/80">{icon}</span>}
      </div>
      <p className="kpi-value mt-3">{renderedValue}</p>
      {(helper || helperBadge) && (
        <div className="mt-3 flex items-center gap-2 text-xs text-textSubtle">
          {helperBadge && <span className={badgeClass}>{helperBadge}</span>}
          {helper && <span className="leading-snug">{helper}</span>}
        </div>
      )}
    </article>
  );
}
