"use client";

type StageStatus = "pending" | "active" | "done" | "skipped" | "error";

type Stage = {
  key: string;
  label: string;
  description?: string;
  status: StageStatus;
  detail?: string | null;
};

type Props = {
  stages: Stage[];
};

const dotClass: Record<StageStatus, string> = {
  pending: "bg-surface-3 border-line",
  active: "bg-emerald-500 border-emerald-300 animate-pulseSoft",
  done: "bg-emerald-400 border-emerald-300",
  skipped: "bg-surface-3 border-line text-textMuted",
  error: "bg-rose/30 border-rose",
};

const labelClass: Record<StageStatus, string> = {
  pending: "text-textMuted",
  active: "text-textMain",
  done: "text-textMain",
  skipped: "text-textMuted",
  error: "text-rose",
};

export function StageTimeline({ stages }: Props) {
  return (
    <ol className="relative space-y-4 border-l border-line pl-6">
      {stages.map((stage) => (
        <li key={stage.key} className="relative">
          <span
            className={`absolute -left-[33px] top-1.5 grid h-4 w-4 place-items-center rounded-full border ${dotClass[stage.status]}`}
          />
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className={`text-sm font-semibold ${labelClass[stage.status]}`}>{stage.label}</p>
              {stage.description && <p className="text-xs text-textMuted">{stage.description}</p>}
            </div>
            <span className="chip text-textSubtle">
              {stage.status === "active"
                ? "en curso"
                : stage.status === "done"
                ? "completo"
                : stage.status === "skipped"
                ? "omitido"
                : stage.status === "error"
                ? "error"
                : "pendiente"}
            </span>
          </div>
          {stage.detail && <p className="mt-1 text-xs text-emerald-300/80">{stage.detail}</p>}
        </li>
      ))}
    </ol>
  );
}
