import "./globals.css";
import type { Metadata } from "next";

import { ChatScopeProvider } from "@/components/ChatScopeProvider";
import { FloatingChatbot } from "@/components/FloatingChatbot";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "UPV-EARTH · Planetary Boundaries Lab",
  description:
    "Plataforma científica UPV-EARTH para análisis del corpus, validación metodológica y búsqueda de papers similares con SPECTER2 + FAISS.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className="min-h-screen">
        <ChatScopeProvider>
          <Nav />
          <main className="mx-auto w-full max-w-7xl px-6 pb-24 pt-8 lg:px-10">{children}</main>
          <footer className="mx-auto w-full max-w-7xl px-6 pb-10 lg:px-10">
            <div className="divider-soft mb-4" />
            <p className="text-xs text-textMuted">
              UPV-EARTH · Plataforma analítica para Planetary Boundaries · Embeddings SPECTER2 e índice de similitud
              sobre el corpus UPV · Criterio de calidad: abstract limpio de más de 500 caracteres.
            </p>
          </footer>
          <FloatingChatbot />
        </ChatScopeProvider>
      </body>
    </html>
  );
}
