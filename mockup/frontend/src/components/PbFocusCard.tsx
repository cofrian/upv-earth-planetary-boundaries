"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HorizontalKeywordBars } from "@/components/charts/analytics-charts";
import { apiGet } from "@/lib/api";
import { DistributionResponse, KeywordItem, PBTermItem } from "@/lib/types";

import { formatNumber } from "./format";

type Source = "declared" | "tfidf" | "wordcloud";

type Props = {
  activePb?: string | null;
  source?: Source;
};

const SOURCE_LABEL: Record<Source, string> = {
  declared: "Keywords declaradas (autores)",
  tfidf: "Términos TF-IDF (extraídos del abstract)",
  wordcloud: "Términos más frecuentes en el corpus",
};

export function PbFocusCard({ activePb = null, source: initialSource = "declared" }: Props) {
  const [pbs, setPbs] = useState<{ label: string; value: number }[]>([]);
  const [pb, setPb] = useState<string | null>(activePb);
  const [source, setSource] = useState<Source>(initialSource);
  const [terms, setTerms] = useState<{ keyword: string; value: number }[]>([]);
  const [loading, setLoading] = useState(false);

  // Cargar la distribución una sola vez
  useEffect(() => {
    let cancelled = false;
    apiGet<DistributionResponse>("/analytics/distribution/pb")
      .then((data) => {
        if (cancelled) return;
        setPbs(data.items);
        if (!pb && data.items.length) {
          setPb(data.items[0].label);
        }
      })
      .catch(() => {
        /* no-op */
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cargar términos cuando cambia pb o source
  useEffect(() => {
    if (!pb) return;
    let cancelled = false;
    setLoading(true);
    const encoded = encodeURIComponent(pb);
    const fetchTerms = async () => {
      try {
        if (source === "tfidf") {
          const data = await apiGet<PBTermItem[]>(`/analytics/pb/tfidf-terms?pb_code=${encoded}&limit=12`);
          if (cancelled) return;
          setTerms(data.map((t) => ({ keyword: t.term, value: Math.round(t.value * 1000) / 1000 })));
        } else if (source === "wordcloud") {
          const data = await apiGet<PBTermItem[]>(`/analytics/pb/wordcloud-terms?pb_code=${encoded}&limit=15`);
          if (cancelled) return;
          setTerms(data.map((t) => ({ keyword: t.term, value: t.value })));
        } else {
          const data = await apiGet<KeywordItem[]>(`/analytics/keywords/pb/${encoded}?limit=12`);
          if (cancelled) return;
          setTerms(data.map((t) => ({ keyword: t.keyword, value: t.value })));
        }
      } catch {
        if (!cancelled) setTerms([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchTerms();
    return () => {
      cancelled = true;
    };
  }, [pb, source]);

  const selectedItem = useMemo(() => pbs.find((p) => p.label === pb), [pbs, pb]);
  const totalCorpus = useMemo(() => pbs.reduce((s, p) => s + p.value, 0), [pbs]);
  const sharePct = totalCorpus > 0 && selectedItem ? (selectedItem.value / totalCorpus) * 100 : 0;
  const encoded = pb ? encodeURIComponent(pb) : "";

  return (
    <article className="card space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <p className="section-title">Foco por Planetary Boundary</p>
          <h3 className="text-lg font-semibold text-textMain">Perfil temático del PB seleccionado</h3>
          <p className="help-text">
            Cambia de PB y de fuente de términos para ver cómo se caracteriza cada uno. TF-IDF revela términos
            distintivos respecto al resto de PBs, no solo los más frecuentes.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={pb || ""}
            onChange={(e) => setPb(e.target.value)}
            className="select min-w-[12rem]"
          >
            {pbs.map((item) => (
              <option key={item.label} value={item.label}>
                {item.label}
              </option>
            ))}
          </select>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value as Source)}
            className="select min-w-[10rem]"
          >
            <option value="declared">Keywords declaradas</option>
            <option value="tfidf">Términos TF-IDF</option>
            <option value="wordcloud">Más frecuentes</option>
          </select>
        </div>
      </header>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">PB activo</span>
          <span className="stat-value text-emerald-300">{pb || "—"}</span>
        </div>
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">Papers en este PB</span>
          <span className="stat-value">{formatNumber(selectedItem?.value || 0)}</span>
          <span className="text-xs text-textMuted">{sharePct.toFixed(1)}% del corpus indexado</span>
        </div>
        <div className="stat rounded-xl border border-line bg-surface-2 p-4">
          <span className="stat-label">Fuente de términos</span>
          <span className="stat-value text-base">{SOURCE_LABEL[source]}</span>
          {pb && (
            <Link
              href={`/papers?pb=${encoded}`}
              className="mt-1 text-xs font-semibold text-emerald-300 hover:underline"
            >
              Explorar papers de {pb} →
            </Link>
          )}
        </div>
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-textMuted">
          Términos del PB {loading && <span className="ml-2 text-[10px] text-emerald-300">cargando…</span>}
        </p>
        <div className="mt-3">
          <HorizontalKeywordBars data={terms} />
        </div>
      </div>
    </article>
  );
}
