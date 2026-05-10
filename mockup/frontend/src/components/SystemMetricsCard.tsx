"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { RuntimeMetrics } from "@/lib/types";

type Props = {
  /** Intervalo de refresco en ms. */
  pollMs?: number;
  /** Pausa el poll cuando está oculto/no se necesita. */
  paused?: boolean;
};

function clampPct(value: number | null | undefined): number {
  if (value === null || value === undefined || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function tone(pct: number): string {
  if (pct >= 90) return "bg-rose";
  if (pct >= 70) return "bg-amber";
  return "bg-emerald-500";
}

function Bar({
  label,
  pct,
  helper,
}: {
  label: string;
  pct: number;
  helper?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className="text-textMuted uppercase tracking-[0.16em]">{label}</span>
        <span className="font-semibold text-textMain tabular-nums">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
        <div
          className={`h-full rounded-full transition-all duration-500 ${tone(pct)}`}
          style={{ width: `${Math.max(2, clampPct(pct))}%` }}
        />
      </div>
      {helper && <p className="text-[11px] text-textMuted">{helper}</p>}
    </div>
  );
}

export function SystemMetricsCard({ pollMs = 3000, paused = false }: Props) {
  const [metrics, setMetrics] = useState<RuntimeMetrics | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (paused) return;
    let cancelled = false;

    const fetchOnce = async () => {
      try {
        const data = await apiGet<RuntimeMetrics>("/analytics/runtime/metrics");
        if (!cancelled) {
          setMetrics(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    };

    void fetchOnce();
    const timer = setInterval(fetchOnce, pollMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [pollMs, paused]);

  const cpu = clampPct(metrics?.cpu_pct);
  const ram = clampPct(metrics?.ram_pct);
  const ramHelper =
    metrics && metrics.ram_used_mb !== null && metrics.ram_total_mb !== null
      ? `${(Number(metrics.ram_used_mb) / 1024).toFixed(1)} / ${(Number(metrics.ram_total_mb) / 1024).toFixed(1)} GB en uso`
      : undefined;

  const hasGpu =
    metrics?.gpu_util_pct !== null &&
    metrics?.gpu_util_pct !== undefined;
  const gpuUtil = clampPct(metrics?.gpu_util_pct);
  const gpuMem = clampPct(metrics?.gpu_mem_util_pct);
  const gpuPower = metrics?.gpu_power_w ?? null;

  return (
    <article className="card space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="section-title">Recursos del dispositivo</p>
          <h3 className="text-lg font-semibold tracking-tight text-textMain">
            Uso en vivo de CPU, RAM y GPU
          </h3>
        </div>
        <span className={metrics ? "chip-accent" : "chip"}>
          {metrics ? "actualización en vivo" : "sin datos"}
        </span>
      </header>

      {error && !metrics && (
        <div className="rounded-xl border border-rose/40 bg-rose/10 p-3 text-xs text-rose">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Bar label="CPU" pct={cpu} helper="Carga total del proceso." />
        <Bar label="RAM" pct={ram} helper={ramHelper} />
        {hasGpu ? (
          <Bar
            label="GPU · uso"
            pct={gpuUtil}
            helper={
              gpuPower !== null ? `${gpuPower.toFixed(1)} W de potencia actual` : undefined
            }
          />
        ) : (
          <div className="space-y-1.5 rounded-xl border border-line/60 bg-surface-2/50 p-3 text-[11px] text-textMuted">
            <p className="uppercase tracking-[0.16em]">GPU</p>
            <p>No se detecta GPU NVIDIA accesible. Si tienes una, comprueba `nvidia-smi`.</p>
          </div>
        )}
      </div>

      {hasGpu && (
        <Bar
          label="GPU · memoria"
          pct={gpuMem}
          helper="Porcentaje de VRAM ocupada."
        />
      )}
      <p className="help-text">
        Métricas leídas vía `psutil` (CPU/RAM) y `nvidia-smi` (GPU). Ayudan a entender si
        el equipo está saturado durante el análisis del PDF.
      </p>
    </article>
  );
}
