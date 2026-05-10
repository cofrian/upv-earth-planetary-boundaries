"use client";

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type ChatQuickAction = {
  label: string;
  question: string;
};

export type ChatScope = {
  /** Etiqueta del contexto actual ("Dashboard", "Paper subido"…). */
  label: string;
  /** Greeting que verá el usuario al abrir el chat por primera vez. */
  greeting: string;
  /** Sugerencias debajo del greeting. */
  suggestions?: string[];
  /** Botones rápidos. */
  quickActions?: ChatQuickAction[];
  /** Paper actual (página de detalle o resultado del análisis). */
  paperId?: string;
  /** Job actual (página de subida mientras corre el pipeline). */
  jobId?: string;
};

const DEFAULT_SCOPE: ChatScope = {
  label: "UPV-EARTH",
  greeting:
    "Hola. Puedo responder sobre el corpus UPV: número de papers, distribución por año o por PB, calidad de abstracts, embeddings y metodología. Si abres un paper, también lo explico contigo. ¿Por dónde empezamos?",
  suggestions: [
    "¿Cuántos papers tiene el corpus válido?",
    "¿Qué distribución hay por Planetary Boundary?",
    "¿Por qué se filtran abstracts cortos?",
    "¿Qué cubre el M2?",
  ],
};

type ChatScopeContextValue = {
  scope: ChatScope;
  setScope: (partial: Partial<ChatScope>) => void;
  resetScope: () => void;
};

const ChatScopeContext = createContext<ChatScopeContextValue | null>(null);

export function ChatScopeProvider({ children }: { children: ReactNode }) {
  const [scope, setScopeState] = useState<ChatScope>(DEFAULT_SCOPE);

  const setScope = useCallback((partial: Partial<ChatScope>) => {
    setScopeState((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetScope = useCallback(() => {
    setScopeState(DEFAULT_SCOPE);
  }, []);

  const value = useMemo(() => ({ scope, setScope, resetScope }), [scope, setScope, resetScope]);

  return <ChatScopeContext.Provider value={value}>{children}</ChatScopeContext.Provider>;
}

export function useChatScope(): ChatScopeContextValue {
  const ctx = useContext(ChatScopeContext);
  if (!ctx) {
    throw new Error("useChatScope debe usarse dentro de <ChatScopeProvider>.");
  }
  return ctx;
}

/**
 * Empuja un scope al contexto mientras el componente está montado y lo
 * limpia al desmontarse. Útil para que páginas client-side (como /upload)
 * comuniquen su jobId al chatbot flotante sin acoplarse a él.
 */
export function usePushChatScope(partial: Partial<ChatScope> | null) {
  const { setScope, resetScope } = useChatScope();
  const serialized = JSON.stringify(partial ?? null);

  useEffect(() => {
    if (!partial) return;
    setScope(partial);
    return () => {
      resetScope();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serialized]);
}
