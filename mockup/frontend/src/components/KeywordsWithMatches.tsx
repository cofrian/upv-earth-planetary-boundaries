import { KeywordItem } from "@/lib/types";

type Props = {
  title: string;
  helper: string | null;
  words: string[];
  /** Subconjunto de `words` que coincide con las top keywords del PB,
   *  con frecuencia en el PB. */
  overlap: KeywordItem[];
  pbCode: string;
  emptyText: string;
};

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

export function KeywordsWithMatches({
  title,
  helper,
  words,
  overlap,
  pbCode,
  emptyText,
}: Props) {
  const matches = new Map(overlap.map((item) => [normalize(item.keyword), item.value]));
  const matchCount = words.reduce((acc, w) => (matches.has(normalize(w)) ? acc + 1 : acc), 0);
  const total = words.length;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="section-title">{title}</p>
        {total > 0 && (
          <span className="text-[11px] text-textMuted tabular-nums">
            {matchCount} / {total} coinciden con top del PB {pbCode || "—"}
          </span>
        )}
      </div>
      {helper && <p className="text-xs text-textMuted">{helper}</p>}

      {total === 0 ? (
        <p className="text-sm text-textMuted">{emptyText}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {words.map((word) => {
            const freq = matches.get(normalize(word));
            const isMatch = freq !== undefined;
            return (
              <span
                key={word}
                className={isMatch ? "chip-accent" : "chip text-textSubtle"}
                title={
                  isMatch
                    ? `Aparece ${freq} veces entre las top keywords del PB ${pbCode}`
                    : `No está entre las top keywords del PB ${pbCode}`
                }
              >
                {word}
                {isMatch && (
                  <span className="ml-1 text-[10px] tabular-nums">×{freq}</span>
                )}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
