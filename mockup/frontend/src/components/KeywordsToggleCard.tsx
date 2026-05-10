"use client";

import { useState } from "react";

import { HorizontalKeywordBars } from "@/components/charts/analytics-charts";
import { KeywordItem } from "@/lib/types";

type Source = "declared" | "unigrams";

type Props = {
  declared: KeywordItem[];
  unigrams: KeywordItem[];
};

const COPY: Record<Source, { title: string; subtitle: string; help: string }> = {
  declared: {
    title: "Keywords declaradas por los autores",
    subtitle: "Sobre el campo `keywords` de cada paper",
    help:
      "Términos que los propios autores declaran en la metadata. Solo aparece para los papers que sí incluyen ese campo: si la mayoría no lo trae, este gráfico no es representativo del corpus.",
  },
  unigrams: {
    title: "Términos más frecuentes en el corpus",
    subtitle: "Conteo sobre los abstracts limpios (sin stopwords)",
    help:
      "Frecuencia bruta de palabras (unigramas) sobre los abstracts limpios. Es independiente del campo keywords y por tanto siempre disponible. Se eliminan stopwords y caracteres no alfabéticos.",
  },
};

export function KeywordsToggleCard({ declared, unigrams }: Props) {
  const declaredAvailable = declared.length > 0;
  const unigramsAvailable = unigrams.length > 0;
  const initial: Source = declaredAvailable ? "declared" : "unigrams";
  const [source, setSource] = useState<Source>(initial);

  const data = source === "declared" ? declared : unigrams;
  const copy = COPY[source];

  return (
    <article className="card space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <p className="section-title">Vocabulario del corpus</p>
          <h3 className="text-lg font-semibold text-textMain">{copy.title}</h3>
          <p className="text-xs text-textMuted">{copy.subtitle}</p>
        </div>
        <div className="inline-flex rounded-full border border-line bg-surface-2 p-1 text-xs">
          <button
            type="button"
            disabled={!declaredAvailable}
            onClick={() => setSource("declared")}
            title={
              declaredAvailable
                ? "Mostrar keywords declaradas por los autores"
                : "No hay keywords declaradas en este corpus"
            }
            className={`rounded-full px-3 py-1.5 font-semibold transition ${
              source === "declared"
                ? "bg-emerald-500/20 text-emerald-300"
                : declaredAvailable
                  ? "text-textSubtle hover:text-emerald-300"
                  : "cursor-not-allowed text-textMuted/50"
            }`}
          >
            Keywords declaradas
          </button>
          <button
            type="button"
            disabled={!unigramsAvailable}
            onClick={() => setSource("unigrams")}
            title={
              unigramsAvailable
                ? "Mostrar palabras más frecuentes en los abstracts del corpus"
                : "No hay unigramas precalculados en este corpus"
            }
            className={`rounded-full px-3 py-1.5 font-semibold transition ${
              source === "unigrams"
                ? "bg-emerald-500/20 text-emerald-300"
                : unigramsAvailable
                  ? "text-textSubtle hover:text-emerald-300"
                  : "cursor-not-allowed text-textMuted/50"
            }`}
          >
            Más frecuentes
          </button>
        </div>
      </header>

      <HorizontalKeywordBars data={data} />

      <p className="help-text border-t border-line/60 pt-3">{copy.help}</p>
    </article>
  );
}
