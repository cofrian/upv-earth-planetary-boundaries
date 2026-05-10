"use client";

import { useMemo, useState } from "react";

import { KeywordItem } from "@/lib/types";

type Source = "declared" | "terms";

type Props = {
  pbCode: string;
  /** Intersección keywords-declaradas ∩ top PB. */
  declared: KeywordItem[];
  /** Intersección términos-frecuentes ∩ top PB. */
  terms: KeywordItem[];
  /** Listas completas para mostrar en ambas columnas. */
  paperKeywords: string[];
  paperTerms: string[];
  pbTopKeywords: KeywordItem[];
};

const COPY: Record<Source, { title: string; help: string; paperColumnTitle: string }> = {
  declared: {
    title: "Coincidencias entre keywords declaradas y top keywords del PB",
    help: "Compara las keywords que el autor declaró en la metadata con las más frecuentes en el PB. Solo aplica si el paper trae el campo keywords.",
    paperColumnTitle: "Keywords del paper",
  },
  terms: {
    title: "Coincidencias entre términos frecuentes del paper y top keywords del PB",
    help: "Usa los términos más repetidos en el abstract del paper (sin stopwords) y mide cuántos están entre las palabras clave del PB. Funciona aunque el paper no traiga keywords declaradas.",
    paperColumnTitle: "Términos del abstract",
  },
};

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

export function PaperOverlapCard({
  pbCode,
  declared,
  terms,
  paperKeywords,
  paperTerms,
  pbTopKeywords,
}: Props) {
  const declaredAvailable = paperKeywords.length > 0;
  const termsAvailable = paperTerms.length > 0;
  const initial: Source = declaredAvailable ? "declared" : "terms";
  const [source, setSource] = useState<Source>(initial);

  const overlapItems = source === "declared" ? declared : terms;
  const paperList = source === "declared" ? paperKeywords : paperTerms;
  const copy = COPY[source];

  const overlapSet = useMemo(
    () => new Set(overlapItems.map((item) => normalize(item.keyword))),
    [overlapItems],
  );

  const paperTotal = paperList.length;
  const matchCount = overlapItems.length;
  const matchPct = paperTotal > 0 ? (matchCount / paperTotal) * 100 : 0;

  return (
    <article className="card space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div className="space-y-0.5">
          <p className="section-title">Overlap con su PB</p>
          <h4 className="text-sm font-semibold text-textMain">{copy.title}</h4>
        </div>
        <div className="inline-flex rounded-full border border-line bg-surface-2 p-1 text-xs">
          <button
            type="button"
            disabled={!declaredAvailable}
            title={
              declaredAvailable
                ? `Keywords declaradas (${paperKeywords.length})`
                : "Este paper no trae keywords declaradas"
            }
            onClick={() => setSource("declared")}
            className={`rounded-full px-3 py-1 font-semibold transition ${
              source === "declared"
                ? "bg-emerald-500/20 text-emerald-300"
                : declaredAvailable
                  ? "text-textSubtle hover:text-emerald-300"
                  : "cursor-not-allowed text-textMuted/50"
            }`}
          >
            Declaradas ({paperKeywords.length})
          </button>
          <button
            type="button"
            disabled={!termsAvailable}
            title={
              termsAvailable
                ? `Términos frecuentes del abstract (${paperTerms.length})`
                : "No hay términos precalculados para este paper"
            }
            onClick={() => setSource("terms")}
            className={`rounded-full px-3 py-1 font-semibold transition ${
              source === "terms"
                ? "bg-emerald-500/20 text-emerald-300"
                : termsAvailable
                  ? "text-textSubtle hover:text-emerald-300"
                  : "cursor-not-allowed text-textMuted/50"
            }`}
          >
            Frecuentes ({paperTerms.length})
          </button>
        </div>
      </header>

      <div className="rounded-xl border border-line/60 bg-surface-2/40 p-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs">
          <span className="text-textMuted uppercase tracking-[0.16em]">
            Coincidencias
          </span>
          <span className="font-semibold text-textMain tabular-nums">
            {matchCount} de {paperTotal} ({matchPct.toFixed(0)}%)
          </span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
          <div
            className={`h-full rounded-full transition-all ${
              matchCount > 0 ? "bg-emerald-500" : "bg-rose/70"
            }`}
            style={{ width: `${Math.max(2, matchPct)}%` }}
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <p className="section-title">{copy.paperColumnTitle}</p>
            <span className="text-[11px] text-textMuted tabular-nums">
              {paperTotal} en total
            </span>
          </div>
          {paperList.length === 0 ? (
            <p className="rounded-xl border border-dashed border-line bg-surface-2 px-3 py-2 text-xs text-textMuted">
              {source === "declared"
                ? "Este paper no trae keywords declaradas en su metadata."
                : "No hay términos precalculados para este paper."}
            </p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {paperList.map((word) => {
                const isMatch = overlapSet.has(normalize(word));
                return (
                  <span
                    key={word}
                    className={isMatch ? "chip-accent" : "chip text-textSubtle"}
                    title={
                      isMatch
                        ? `Está entre las top keywords del PB ${pbCode}`
                        : `No está entre las top keywords del PB ${pbCode}`
                    }
                  >
                    {word}
                    {isMatch && <span aria-hidden className="ml-1">✓</span>}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <p className="section-title">Top del PB {pbCode}</p>
            <span className="text-[11px] text-textMuted tabular-nums">
              {pbTopKeywords.length} en total
            </span>
          </div>
          {pbTopKeywords.length === 0 ? (
            <p className="rounded-xl border border-dashed border-line bg-surface-2 px-3 py-2 text-xs text-textMuted">
              No hay top keywords disponibles para este PB.
            </p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {pbTopKeywords.map((item) => {
                const isMatch = overlapSet.has(normalize(item.keyword));
                return (
                  <span
                    key={item.keyword}
                    className={
                      isMatch
                        ? "chip-accent"
                        : "chip text-textSubtle"
                    }
                    title={
                      isMatch
                        ? `También aparece en este paper · frecuencia ${item.value} en el PB`
                        : `Frecuencia ${item.value} en el PB · no aparece en este paper`
                    }
                  >
                    {item.keyword}
                    <span className="ml-1 text-[10px] text-textMuted tabular-nums">
                      ×{item.value}
                    </span>
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {matchCount === 0 && paperTotal > 0 && (
        <p className="rounded-xl border border-amber/40 bg-amber/10 p-3 text-xs leading-relaxed text-amber">
          Ninguna palabra del paper aparece en las top keywords del PB {pbCode}.
          Esto puede indicar que el paper trata el PB desde un ángulo poco habitual o
          que la asignación se basa en señales semánticas (SPECTER2) más que léxicas.
        </p>
      )}

      <p className="help-text border-t border-line/60 pt-3">{copy.help}</p>
    </article>
  );
}
