"use client";

import { usePushChatScope } from "@/components/ChatScopeProvider";

type PaperChatScopeProps = {
  paperId: string;
  title: string | null | undefined;
};

/**
 * Empuja al chatbot flotante el scope de un paper concreto (greeting +
 * botones rápidos). La página de detalle es un server component, así que
 * no puede llamar hooks; este wrapper lo hace por ella.
 */
export function PaperChatScope({ paperId, title }: PaperChatScopeProps) {
  usePushChatScope({
    label: "Paper analizado",
    paperId,
    greeting: `Puedo explicarte el resultado de "${title || "este paper"}": resumir el abstract, justificar el PB asignado y comentar por qué los papers similares se parecen. ¿Qué te interesa?`,
    quickActions: [
      { label: "Resume este paper", question: "Resume el abstract de este paper en 4-6 frases." },
      { label: "Explícame los PBs", question: "Explícame qué Planetary Boundaries se le han asignado y por qué, usando los scores ya calculados." },
      { label: "¿Por qué son similares?", question: "Mira los papers similares listados y explica por qué se parecen a éste a partir de sus títulos y previews de abstract." },
      { label: "¿Es válido para el corpus?", question: "¿Este paper cumple los criterios del corpus válido para embeddings? Justifica con la longitud del abstract y el filtro >500 caracteres." },
    ],
    suggestions: undefined,
  });
  return null;
}
