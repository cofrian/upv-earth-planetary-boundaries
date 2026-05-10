import Link from "next/link";

import { SimilarPaper } from "@/lib/types";
import { shortText } from "./format";

type Props = {
  items: SimilarPaper[];
  emptyMessage?: string;
  modelLabel?: string;
};

export function SimilarPapersList({ items, emptyMessage, modelLabel = "SPECTER2" }: Props) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface-2 p-6 text-sm text-textMuted">
        {emptyMessage ||
          "Aún no se ha generado un embedding para comparar contra el corpus. Si el abstract supera los 500 caracteres, el sistema mostrará aquí los vecinos más cercanos."}
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li
          key={item.doc_id}
          className="rounded-2xl border border-line bg-surface-2 p-5 transition hover:border-emerald-500/40 hover:bg-surface-3"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <h4 className="text-base font-semibold text-textMain leading-snug">
                {item.paper_id ? (
                  <Link href={`/papers/${item.paper_id}`} className="hover:text-emerald-300 hover:underline">
                    {item.title || "Sin título"}
                  </Link>
                ) : (
                  item.title || "Sin título"
                )}
              </h4>
              <p className="text-xs text-textMuted">
                {item.journal || "Journal n/d"} · {item.year ?? "Año n/d"}
                {item.doi ? (
                  <>
                    {" · "}
                    <a
                      href={`https://doi.org/${item.doi}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-emerald-300 hover:underline"
                    >
                      DOI {item.doi} ↗
                    </a>
                  </>
                ) : null}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="chip-accent">similitud {(item.score * 100).toFixed(1)}%</span>
              {item.pb_code && <span className="chip">{item.pb_code}</span>}
              <span className="chip">{modelLabel}</span>
            </div>
          </div>
          {item.abstract_preview && (
            <p className="mt-3 text-sm leading-relaxed text-textSubtle">{shortText(item.abstract_preview, 360)}</p>
          )}
          {item.keywords?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {item.keywords.slice(0, 6).map((kw) => (
                <span key={kw} className="chip text-textSubtle">
                  {kw}
                </span>
              ))}
            </div>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line/40 pt-3 text-xs">
            {item.paper_id ? (
              <Link
                href={`/papers/${item.paper_id}`}
                className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
              >
                Ver análisis interno →
              </Link>
            ) : (
              <span className="text-textMuted">
                Análisis interno no disponible (paper no presente en la base UPV).
              </span>
            )}
            {item.doi && (
              <a
                href={`https://doi.org/${item.doi}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-textSubtle transition hover:border-emerald-500/40 hover:text-emerald-300"
              >
                Abrir artículo (DOI) ↗
              </a>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
