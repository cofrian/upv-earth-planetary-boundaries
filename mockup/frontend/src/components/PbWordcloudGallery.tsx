"use client";

import { useState } from "react";

type Item = {
  pb_code: string;
  count: number;
};

type Props = {
  items: Item[];
};

function shortPb(code: string): string {
  const m = code.match(/^(\d+)/);
  if (m) return `PB${m[1]}`;
  return code.slice(0, 4);
}

export function PbWordcloudGallery({ items }: Props) {
  const [activeIdx, setActiveIdx] = useState(0);
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface-2 p-6 text-sm text-textMuted">
        No hay wordclouds precalculados disponibles.
      </div>
    );
  }
  const safeIdx = Math.min(activeIdx, items.length - 1);
  const active = items[safeIdx];
  const url = `/api/v1/analytics/pb/wordcloud-image?pb_code=${encodeURIComponent(active.pb_code)}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {items.map((item, idx) => {
          const isActive = idx === safeIdx;
          return (
            <button
              key={item.pb_code}
              type="button"
              onClick={() => setActiveIdx(idx)}
              title={item.pb_code}
              className={`rounded-full border px-3 py-1 text-xs font-mono transition ${
                isActive
                  ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-300"
                  : "border-line bg-surface-2 text-textSubtle hover:border-emerald-500/40 hover:text-emerald-300"
              }`}
            >
              <span className="font-semibold">{shortPb(item.pb_code)}</span>{" "}
              <span className="text-textMuted">{item.count}</span>
            </button>
          );
        })}
      </div>

      <div className="rounded-2xl border border-line bg-surface-2 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3">
          <div className="space-y-0.5">
            <p className="text-xs uppercase tracking-[0.16em] text-textMuted">PB activo</p>
            <p className="text-sm font-semibold text-textMain">{active.pb_code}</p>
          </div>
          <span className="chip">{active.count} papers</span>
        </div>
        <div className="overflow-hidden rounded-xl bg-bg/60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt={`Wordcloud de ${active.pb_code}`}
            className="block w-full"
            loading="lazy"
          />
        </div>
      </div>
    </div>
  );
}
