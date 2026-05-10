const publicBase = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";
const internalBase = process.env.API_BASE_URL_INTERNAL || "http://127.0.0.1:8000/api/v1";

function resolveBase(): string {
  const isServer = typeof window === "undefined";
  if (isServer && publicBase.startsWith("/")) {
    return internalBase;
  }
  return publicBase;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${resolveBase()}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiUploadPdf(file: File): Promise<{ job_id: string; status: string; message: string }> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${resolveBase()}/uploads/pdf`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.detail || "No se pudo subir el PDF");
  }

  return response.json();
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${resolveBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type ChatStreamEvent =
  | { type: "meta"; context: Record<string, unknown> }
  | { type: "token"; content: string }
  | { type: "done"; duration_sec?: number }
  | { type: "error"; enabled?: boolean; message: string };

export async function chatStream(
  body: { question: string; paper_id?: string; job_id?: string; include_analytics?: boolean },
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${resolveBase()}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.detail || `Chat stream error ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let separatorIdx = buffer.indexOf("\n\n");
    while (separatorIdx >= 0) {
      const rawEvent = buffer.slice(0, separatorIdx);
      buffer = buffer.slice(separatorIdx + 2);
      separatorIdx = buffer.indexOf("\n\n");

      const lines = rawEvent.split("\n");
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload) continue;
        if (payload === "[DONE]") return;
        try {
          const parsed = JSON.parse(payload) as ChatStreamEvent;
          onEvent(parsed);
        } catch {
          // ignorar líneas malformadas
        }
      }
    }
  }
}
