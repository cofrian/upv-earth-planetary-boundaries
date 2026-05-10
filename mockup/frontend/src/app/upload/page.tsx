"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AbstractValidationCard } from "@/components/AbstractValidationCard";
import { usePushChatScope } from "@/components/ChatScopeProvider";
import { SimilarPapersList } from "@/components/SimilarPapersList";
import { StageTimeline } from "@/components/StageTimeline";
import { SystemMetricsCard } from "@/components/SystemMetricsCard";
import { formatNumber, modelLabel } from "@/components/format";
import { apiGet, apiUploadPdf } from "@/lib/api";
import {
  IndexStatus,
  Job,
  JobEvent,
  JobResult,
} from "@/lib/types";

type StageStatus = "pending" | "active" | "done" | "skipped" | "error";

type StageView = {
  key: string;
  label: string;
  description: string;
  status: StageStatus;
  detail?: string | null;
};

const STAGES: { key: string; label: string; description: string }[] = [
  { key: "upload", label: "Subida del PDF", description: "Validación y guardado del archivo." },
  { key: "parse_pdf", label: "Extracción de texto", description: "Lectura del contenido del PDF." },
  { key: "extract_abstract", label: "Detección del abstract", description: "Identificación de la sección del abstract." },
  { key: "clean_text", label: "Limpieza semántica", description: "Normalización conservadora del texto." },
  { key: "validate_abstract", label: "Validación del abstract", description: "Comprobación del criterio de calidad (más de 500 caracteres)." },
  { key: "generate_embedding", label: "Embedding SPECTER2", description: "Representación con título + abstract limpio." },
  { key: "similarity_search", label: "Búsqueda de similares", description: "Vecinos cercanos en el corpus UPV." },
  { key: "pb_scoring", label: "Inferencia Planetary Boundaries", description: "Asignación de PB principal y secundarios." },
  { key: "summarize", label: "Resumen", description: "Resumen extractivo del abstract." },
  { key: "persist", label: "Persistencia", description: "Almacenamiento del análisis en la plataforma." },
];

const STAGE_INDEX = STAGES.reduce<Record<string, number>>((acc, stage, idx) => {
  acc[stage.key] = idx;
  return acc;
}, {});

function buildStages(job: Job | null, events: JobEvent[]): StageView[] {
  const finished = events.map((event) => event.event_type);
  const currentIdx = job?.stage ? STAGE_INDEX[job.stage] ?? -1 : -1;

  return STAGES.map((stage, idx) => {
    const reached = finished.includes(stage.key);
    let status: StageStatus = "pending";
    if (job?.status === "failed" && idx === currentIdx) status = "error";
    else if (reached) status = "done";
    else if (idx === currentIdx) status = "active";
    else if (idx < currentIdx) status = "done";

    let detail: string | null = null;
    const last = [...events].reverse().find((event) => event.event_type === stage.key);
    if (last) {
      const payload = last.event_payload || {};
      if (stage.key === "parse_pdf" && payload.chars !== undefined) {
        detail = `${formatNumber(Number(payload.chars))} caracteres extraídos`;
      } else if (stage.key === "extract_abstract" && payload.chars !== undefined) {
        detail = `${formatNumber(Number(payload.chars))} caracteres detectados como abstract`;
      } else if (stage.key === "clean_text" && payload.abstract_norm_chars !== undefined) {
        const passes = payload.passes_threshold ? "supera 500" : "abstract corto";
        detail = `${formatNumber(Number(payload.abstract_norm_chars))} caracteres tras la limpieza · ${passes}`;
      } else if (stage.key === "validate_abstract" && payload.abstract_char_len !== undefined) {
        detail = `${payload.abstract_char_len} caracteres · ${
          payload.passes_threshold ? "cumple el criterio de calidad" : "por debajo del umbral de 500"
        }`;
      } else if (stage.key === "generate_embedding") {
        const dim = payload.embedding_dim || 0;
        const modelName = String(payload.model_id || "").includes("specter")
          ? "SPECTER2"
          : "modelo de embeddings";
        detail = `${modelName} · ${dim} dimensiones · título + abstract limpio`;
      } else if (stage.key === "similarity_search") {
        if (payload.skipped) detail = "omitido porque el abstract es demasiado corto";
        else detail = `${payload.results || 0} papers similares recuperados`;
      } else if (stage.key === "pb_scoring" && payload.top_pb_code) {
        detail = `PB principal: ${payload.top_pb_code}`;
      }
    }

    if (status === "pending" && stage.key === "similarity_search") {
      const validation = events.find((event) => event.event_type === "validate_abstract");
      if (validation && validation.event_payload?.passes_threshold === false) {
        return { ...stage, status: "skipped", detail: "se omite porque el abstract no alcanza los 500 caracteres" };
      }
    }

    return { ...stage, status, detail };
  });
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [error, setError] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const stages = useMemo(() => buildStages(job, events), [job, events]);
  const canUpload = useMemo(() => !!file && !submitting, [file, submitting]);

  const analysisDone = result?.job?.paper_id != null;
  usePushChatScope({
    label: "Paper subido",
    paperId: result?.job?.paper_id || undefined,
    jobId: job?.id,
    greeting: analysisDone
      ? "El análisis ha terminado. Puedo resumirte el paper, explicarte los PBs detectados o por qué los papers similares se parecen al tuyo."
      : "Cuando termine el análisis del PDF tendré acceso al abstract, los PBs y los papers similares para responderte. Sube un paper para empezar.",
    quickActions: [
      { label: "Resume este paper", question: "Resume el abstract de este paper en 4-6 frases." },
      { label: "Explícame los PBs", question: "Explícame qué Planetary Boundaries se le han asignado y por qué, usando los scores ya calculados." },
      { label: "¿Por qué son similares?", question: "Mira los papers similares listados y explica por qué se parecen al subido." },
      { label: "¿Es válido para el corpus?", question: "¿Este paper cumple los criterios del corpus válido para embeddings? Justifica con la longitud del abstract y el filtro >500 caracteres." },
    ],
    suggestions: undefined,
  });

  useEffect(() => {
    let cancelled = false;
    apiGet<IndexStatus>("/analytics/index-status")
      .then((data) => {
        if (!cancelled) setIndexStatus(data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const pollJob = useCallback((jobId: string) => {
    const timer = setInterval(async () => {
      try {
        const [status, jobEvents] = await Promise.all([
          apiGet<Job>(`/jobs/${jobId}`),
          apiGet<JobEvent[]>(`/jobs/${jobId}/events?limit=200`),
        ]);
        setJob(status);
        setEvents(jobEvents);
        if (status.status === "completed" || status.status === "failed") {
          clearInterval(timer);
          const finalResult = await apiGet<JobResult>(`/jobs/${jobId}/result`);
          setResult(finalResult);
        }
      } catch (err) {
        clearInterval(timer);
        setError((err as Error).message);
      }
    }, 2000);
  }, []);

  const submit = useCallback(async () => {
    if (!file) return;
    setSubmitting(true);
    setError("");
    setResult(null);
    setEvents([]);
    setJob(null);
    try {
      const uploaded = await apiUploadPdf(file);
      pollJob(uploaded.job_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [file, pollJob]);

  const onDrop = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragActive(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped && dropped.type === "application/pdf") {
      setFile(dropped);
    }
  };

  const validation = result?.abstract_validation || null;
  const embeddingInfo = result?.embedding_info || null;
  const summary = result?.summary || null;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <span className="chip-accent">Subida y análisis</span>
        <h1 className="text-3xl font-semibold tracking-tight">Sube un paper y revisa el flujo SPECTER2</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-textSubtle">
          La plataforma extrae el abstract, comprueba que cumple el criterio de calidad, genera el embedding con{" "}
          {modelLabel(indexStatus?.model_id)} y devuelve los papers más similares dentro del corpus UPV. Cada etapa
          se muestra con su estado y métricas relevantes.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[2fr_3fr]">
        <article className="card space-y-4">
          <p className="section-title">Paper</p>
          <label
            htmlFor="pdf-input"
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={onDrop}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-6 py-10 text-center transition ${
              dragActive ? "border-emerald-500 bg-emerald-500/10" : "border-line bg-surface-2 hover:border-emerald-500/40"
            }`}
          >
            <span className="text-sm font-semibold text-textMain">
              {file ? file.name : "Arrastra el PDF aquí o haz clic para seleccionar"}
            </span>
            <span className="mt-1 text-xs text-textMuted">
              {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "Solo se aceptan archivos .pdf"}
            </span>
            <input
              id="pdf-input"
              ref={inputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={submit} disabled={!canUpload} className="btn-primary">
              {submitting ? "Subiendo…" : "Procesar PDF"}
            </button>
            {file && (
              <button
                onClick={() => {
                  setFile(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
                className="btn-ghost"
              >
                Quitar archivo
              </button>
            )}
          </div>
          {error && (
            <div className="rounded-xl border border-rose/40 bg-rose/10 p-3 text-sm text-rose">
              {error}
            </div>
          )}
        </article>

        <article className="card space-y-3">
          <p className="section-title">Pipeline en directo</p>
          <h3 className="text-lg font-semibold">Estado por etapa</h3>
          <StageTimeline stages={stages} />
          {job && (
            <div className="rounded-xl border border-line bg-surface-2 p-4 text-xs text-textSubtle">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  <span className="text-textMuted">Identificador:</span>{" "}
                  <span className="font-mono">{job.id.slice(0, 8)}…</span>
                </span>
                <span>
                  <span className="text-textMuted">Estado:</span>{" "}
                  <span className={job.status === "failed" ? "text-rose" : "text-emerald-300"}>{job.status}</span>{" "}
                  · {job.progress_pct}%
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${Math.max(4, job.progress_pct)}%` }}
                />
              </div>
            </div>
          )}
        </article>
      </section>

      <section className="card flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <p className="section-title">Modelo activo</p>
          <p className="text-base font-semibold text-textMain">{modelLabel(indexStatus?.model_id)}</p>
          <p className="text-xs text-textMuted">Representación: título + abstract limpio.</p>
        </div>
        <div className="flex flex-wrap gap-1.5 text-xs">
          <span className={indexStatus?.is_specter ? "chip-accent" : "chip-warn"}>
            {indexStatus?.is_specter ? "SPECTER2" : "modelo alternativo"}
          </span>
          <span className="chip">{indexStatus?.embedding_dim || "—"} dimensiones</span>
          <span className="chip">{formatNumber(indexStatus?.candidates || 0)} papers candidatos</span>
        </div>
      </section>

      <SystemMetricsCard pollMs={3000} />

      <AbstractValidationCard validation={validation} embedding={embeddingInfo} />

      {result?.pb_result && (
        <section className="card space-y-3">
          <p className="section-title">Planetary Boundaries estimadas</p>
          <h3 className="text-lg font-semibold text-textMain">
            PB principal: {result.pb_result.top_pb_code}
            <span className="ml-2 text-sm font-normal text-textMuted">
              · confianza {(result.pb_result.top_pb_score * 100).toFixed(1)}%
            </span>
          </h3>
          <p className="text-sm leading-relaxed text-textSubtle">{result.pb_result.explanation_text}</p>
        </section>
      )}

      {summary && (
        <section className="card space-y-2">
          <p className="section-title">Resumen del abstract</p>
          <p className="text-sm leading-relaxed text-textMain">{summary}</p>
        </section>
      )}

      <section className="card space-y-4">
        <header className="space-y-1">
          <p className="section-title">Papers similares por contenido</p>
          <h3 className="text-lg font-semibold">Vecinos cercanos en el corpus UPV</h3>
          <p className="help-text">
            La similitud se calcula con el embedding {modelLabel(indexStatus?.model_id)} del paper (título +
            abstract limpio) frente al corpus UPV indexado.
          </p>
        </header>
        <SimilarPapersList
          items={result?.similar_papers || []}
          modelLabel={modelLabel(indexStatus?.model_id)}
          emptyMessage={
            validation && !validation.is_valid_for_embedding
              ? "El abstract no supera 500 caracteres. La búsqueda de similares se omite hasta que el contenido sea suficiente."
              : undefined
          }
        />
      </section>

    </div>
  );
}
