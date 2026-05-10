export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const formatter = new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return formatter.format(value);
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("es-ES", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

export function shortText(text: string | null | undefined, max = 160): string {
  if (!text) return "";
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1).trimEnd()}…`;
}

export function modelLabel(modelId: string | null | undefined): string {
  if (!modelId) return "Sin modelo";
  const lower = modelId.toLowerCase();
  if (lower.includes("specter")) return "SPECTER2";
  if (lower.includes("minilm")) return "Modelo de embeddings (alternativo)";
  return modelId;
}

const FRIENDLY_RULES: Record<string, string> = {
  "abstract_char_len > 500": "abstract limpio > 500 caracteres",
  "title + clean_abstract_semantic": "título + abstract limpio",
};

export function friendlyRule(rule: string | null | undefined): string {
  if (!rule) return "";
  return FRIENDLY_RULES[rule.trim()] ?? rule;
}
