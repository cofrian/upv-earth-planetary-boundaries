"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

import { Chatbot } from "@/components/Chatbot";
import { useChatScope } from "@/components/ChatScopeProvider";

const PAPER_ID_RE = /^\/papers\/([0-9a-f-]{8,})/i;

function deriveScopeLabel(pathname: string): string {
  if (pathname.startsWith("/dashboard")) return "Dashboard";
  if (pathname.startsWith("/papers/")) return "Paper analizado";
  if (pathname === "/papers") return "Explorador de corpus";
  if (pathname.startsWith("/upload")) return "Paper subido";
  if (pathname.startsWith("/analysis")) return "Análisis exploratorio";
  if (pathname.startsWith("/benchmark")) return "Benchmark de modelos";
  return "UPV-EARTH";
}

export function FloatingChatbot() {
  const pathname = usePathname();
  const { scope } = useChatScope();
  const [open, setOpen] = useState(false);

  // Detección automática del paperId cuando el usuario está en /papers/[id].
  const autoPaperId = useMemo(() => {
    const match = pathname.match(PAPER_ID_RE);
    return match ? match[1] : undefined;
  }, [pathname]);

  const effectivePaperId = scope.paperId || autoPaperId;
  const effectiveLabel = scope.paperId || scope.jobId ? scope.label : deriveScopeLabel(pathname);

  // Cerrar el panel con la tecla Escape cuando está abierto.
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <>
      {/* Botón flotante (FAB) */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={open ? "Cerrar chatbot UPV-EARTH" : "Abrir chatbot UPV-EARTH"}
        className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-emerald transition-all hover:scale-105 active:scale-95 ${
          open
            ? "bg-surface-2 text-emerald-300 ring-1 ring-emerald-500/40"
            : "bg-emerald-500 text-[#02140d] hover:bg-emerald-400"
        }`}
      >
        {open ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            className="h-6 w-6"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6L6 18" />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-6 w-6"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7A8.38 8.38 0 0 1 4 11.5a8.5 8.5 0 0 1 4.7-7.6A8.38 8.38 0 0 1 12.5 3h.5a8.48 8.48 0 0 1 8 8v.5z"
            />
          </svg>
        )}
        {!open && (
          <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-emerald-400 ring-2 ring-bg animate-pulseSoft" />
        )}
      </button>

      {/* Panel del chat */}
      {open && (
        <div
          role="dialog"
          aria-label="Chatbot UPV-EARTH"
          className="fixed bottom-24 right-6 z-40 flex w-[calc(100vw-3rem)] max-w-[440px] flex-col rounded-2xl border border-line bg-surface-1 shadow-glow animate-fade-up"
          style={{ height: "min(640px, calc(100vh - 8rem))" }}
        >
          <div className="flex h-full flex-col gap-4 p-5">
            <Chatbot
              bare
              scope={effectiveLabel}
              greeting={scope.greeting}
              paperId={effectivePaperId}
              jobId={scope.jobId}
              quickActions={scope.quickActions}
              suggestions={scope.suggestions}
            />
          </div>
        </div>
      )}
    </>
  );
}
