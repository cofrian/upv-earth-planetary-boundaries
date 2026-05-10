"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiGet, chatStream, type ChatStreamEvent } from "@/lib/api";
import type { ChatHealth } from "@/lib/types";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
  pending?: boolean;
  error?: boolean;
};

type QuickAction = {
  label: string;
  question: string;
};

type ChatbotProps = {
  /** Etiqueta corta que se muestra encima del panel (Dashboard, Paper, etc.). */
  scope: string;
  /** Mensaje inicial del asistente, depende de la página. */
  greeting: string;
  /** UUID del paper actual (página de detalle). */
  paperId?: string;
  /** UUID del job recién subido (página de upload). */
  jobId?: string;
  /** Si false, no se inyecta el snapshot del corpus. Por defecto true. */
  includeAnalytics?: boolean;
  /** Botones rápidos opcionales. */
  quickActions?: QuickAction[];
  /** Sugerencias de preguntas iniciales (pills bajo el greeting). */
  suggestions?: string[];
  /**
   * Si true, no envuelve el contenido en `.card`. Útil cuando se renderiza
   * dentro de un panel flotante que ya provee el chrome.
   */
  bare?: boolean;
};

function genId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function Chatbot({
  scope,
  greeting,
  paperId,
  jobId,
  includeAnalytics = true,
  quickActions,
  suggestions,
  bare = false,
}: ChatbotProps) {
  const [health, setHealth] = useState<ChatHealth | null>(null);
  const [healthChecked, setHealthChecked] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    { id: genId(), role: "assistant", text: greeting },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<ChatHealth>("/chat/health")
      .then((data) => {
        if (!cancelled) {
          setHealth(data);
          setHealthChecked(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth({
            enabled: false,
            available: false,
            model: null,
            base_url: null,
            reason: "No se pudo contactar con el backend",
          });
          setHealthChecked(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, streaming]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const llmUnavailable = useMemo(
    () => !healthChecked || !health?.enabled || !health?.available,
    [healthChecked, health],
  );
  const disabled = useMemo(
    () => streaming || llmUnavailable,
    [streaming, llmUnavailable],
  );

  const send = useCallback(
    async (raw: string) => {
      const question = raw.trim();
      if (!question || streaming) return;
      if (!health?.enabled || !health?.available) return;

      const userMsg: ChatMessage = { id: genId(), role: "user", text: question };
      const assistantId = genId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        text: "",
        pending: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      const updateAssistant = (mutator: (msg: ChatMessage) => ChatMessage) => {
        setMessages((prev) =>
          prev.map((msg) => (msg.id === assistantId ? mutator(msg) : msg)),
        );
      };

      try {
        await chatStream(
          {
            question,
            paper_id: paperId,
            job_id: jobId,
            include_analytics: includeAnalytics,
          },
          (event: ChatStreamEvent) => {
            if (event.type === "token") {
              updateAssistant((msg) => ({ ...msg, text: msg.text + event.content, pending: false }));
            } else if (event.type === "error") {
              updateAssistant((msg) => ({
                ...msg,
                text: msg.text || event.message || "Error al consultar el LLM.",
                pending: false,
                error: true,
              }));
            } else if (event.type === "done") {
              updateAssistant((msg) => ({ ...msg, pending: false }));
            }
          },
          controller.signal,
        );
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          updateAssistant((msg) => ({ ...msg, pending: false }));
        } else {
          updateAssistant((msg) => ({
            ...msg,
            text: msg.text || `Error: ${(err as Error).message}`,
            pending: false,
            error: true,
          }));
        }
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [streaming, health, paperId, jobId, includeAnalytics],
  );

  const onSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void send(input);
    },
    [input, send],
  );

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        void send(input);
      }
    },
    [input, send],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const stateBadge = (() => {
    if (!healthChecked) return { label: "Comprobando…", tone: "chip" };
    if (!health?.enabled) return { label: "Chatbot desactivado", tone: "chip-warn" };
    if (!health?.available) return { label: "LLM no disponible", tone: "chip-warn" };
    return { label: `LLM listo · ${health.model || "modelo"}`, tone: "chip-accent" };
  })();

  const showOfflineBanner =
    healthChecked && (!health?.enabled || !health?.available);

  return (
    <section
      className={
        bare
          ? "flex h-full flex-col gap-4"
          : "card flex h-full flex-col gap-4"
      }
    >
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="section-title">Chatbot UPV-EARTH</p>
          <h3 className="text-lg font-semibold tracking-tight text-textMain">
            Asistente RAG · {scope}
          </h3>
          <p className="help-text">
            Responde sólo con datos calculados por la plataforma. La clasificación PB y los
            similares vienen de SPECTER2 + FAISS, no del LLM.
          </p>
        </div>
        <span className={stateBadge.tone}>{stateBadge.label}</span>
      </header>

      {showOfflineBanner && (
        <div className="rounded-xl border border-amber/40 bg-amber/10 p-3 text-xs leading-relaxed text-amber">
          Chatbot no disponible; el análisis principal sigue funcionando. {" "}
          {health?.reason ? <span className="text-textSubtle">({health.reason})</span> : null}
        </div>
      )}

      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-line/60 bg-surface-2/40 p-3"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-emerald-500 text-[#02140d] shadow-emerald"
                  : msg.error
                  ? "border border-rose/40 bg-rose/10 text-rose"
                  : "border border-line bg-surface-1 text-textMain"
              }`}
            >
              {msg.text || (msg.pending ? "…" : "")}
              {msg.pending && msg.text && (
                <span className="ml-1 inline-block h-2 w-1 animate-pulseSoft rounded-full bg-emerald-400 align-middle" />
              )}
            </div>
          </div>
        ))}
      </div>

      {(suggestions?.length || quickActions?.length) && !streaming && (
        <div className="flex flex-wrap gap-2">
          {quickActions?.map((action) => (
            <button
              key={action.label}
              type="button"
              onClick={() => void send(action.question)}
              disabled={disabled}
              className="btn-ghost text-xs disabled:cursor-not-allowed disabled:opacity-40"
            >
              {action.label}
            </button>
          ))}
          {suggestions?.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => void send(s)}
              disabled={disabled}
              className="chip hover:border-emerald-500/50 hover:text-emerald-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={2}
          disabled={disabled}
          placeholder={
            llmUnavailable
              ? "Chatbot no disponible. Activa LLM_ENABLED y un servidor compatible OpenAI."
              : streaming
              ? "Generando respuesta… pulsa Cancelar para detener."
              : "Escribe tu pregunta sobre el corpus, este paper o la metodología…"
          }
          className="input resize-none disabled:cursor-not-allowed disabled:opacity-50"
        />
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-textMuted">
            Enter para enviar · Shift+Enter para salto de línea
          </span>
          <div className="flex items-center gap-2">
            {streaming ? (
              <button type="button" onClick={cancel} className="btn-ghost text-xs">
                Cancelar
              </button>
            ) : null}
            <button type="submit" disabled={disabled || !input.trim()} className="btn-primary">
              {streaming ? "Generando…" : "Enviar"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
