import Link from "next/link";

import { formatNumber } from "@/components/format";
import { apiGet } from "@/lib/api";
import { Paper, PaperListResponse } from "@/lib/types";

const HIDDEN_DOC_IDS = new Set(["b39624d6c38a"]);
const HIDDEN_TITLE_PATTERNS = ["chapter 34 the role of hydrological modelling uncertainties"];

function isHiddenPaper(docId: string | null, title: string): boolean {
  const docKey = (docId || "").trim().toLowerCase();
  const titleKey = (title || "").trim().toLowerCase();
  if (HIDDEN_DOC_IDS.has(docKey)) return true;
  return HIDDEN_TITLE_PATTERNS.some((pattern) => titleKey.includes(pattern));
}

function pageLink(params: URLSearchParams, page: number): string {
  const next = new URLSearchParams(params);
  next.set("page", String(page));
  return `/papers?${next.toString()}`;
}

function Pill({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "accent" | "warn" }) {
  if (tone === "accent") return <span className="chip-accent">{children}</span>;
  if (tone === "warn") return <span className="chip-warn">{children}</span>;
  return <span className="chip">{children}</span>;
}

export default async function PapersPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;

  const stringParam = (key: string) => (typeof params[key] === "string" ? (params[key] as string) : "");

  const query = stringParam("query");
  const year = stringParam("year");
  const journal = stringParam("journal");
  const pb = stringParam("pb");
  const doi = stringParam("doi");
  const keywords = stringParam("keywords");
  const minLen = stringParam("min_abstract_len");
  const onlyEmbedding = stringParam("only_embedding_valid") === "true";
  const sort = stringParam("sort") || "year_desc";
  const page = stringParam("page") || "1";

  const qs = new URLSearchParams();
  if (query) qs.set("query", query);
  if (year) qs.set("year", year);
  if (journal) qs.set("journal", journal);
  if (pb) qs.set("pb", pb);
  if (doi) qs.set("doi", doi);
  if (keywords) qs.set("keywords", keywords);
  if (minLen) qs.set("min_abstract_len", minLen);
  if (onlyEmbedding) qs.set("only_embedding_valid", "true");
  qs.set("sort", sort);
  qs.set("page", page);
  qs.set("page_size", "20");

  let data: PaperListResponse = { total: 0, page: Number(page), page_size: 20, items: [] };
  let error: string | null = null;
  try {
    data = await apiGet<PaperListResponse>(`/papers?${qs.toString()}`);
  } catch (err) {
    error = (err as Error).message;
  }

  const visibleItems: Paper[] = data.items.filter((paper) => !isHiddenPaper(paper.doc_id, paper.title));
  const hiddenInPage = data.items.length - visibleItems.length;
  const visibleTotal = Math.max(0, data.total - hiddenInPage);

  const totalPages = Math.max(1, Math.ceil(visibleTotal / data.page_size));
  const currentPage = Math.max(1, Math.min(totalPages, Number(page)));

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <span className="chip-accent">Explorador del corpus</span>
        <h1 className="text-3xl font-semibold tracking-tight">Papers del corpus UPV-EARTH</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-textSubtle">
          Búsqueda y filtros sobre los papers que pasaron los filtros del pipeline. La columna{" "}
          <span className="text-emerald-300">embedding</span> indica si el paper forma parte del corpus SPECTER2
          (abstract limpio con más de 500 caracteres) o si se descartó del índice de similitud.
        </p>
      </header>

      <form className="card grid gap-3 md:grid-cols-3 lg:grid-cols-4">
        <input className="input md:col-span-2 lg:col-span-2" name="query" defaultValue={query} placeholder="Buscar por título o abstract" />
        <input className="input" name="year" defaultValue={year} placeholder="Año (1900-2024)" inputMode="numeric" />
        <input className="input" name="pb" defaultValue={pb} placeholder="PB code (ej. 1 - Climate Change)" />
        <input className="input" name="journal" defaultValue={journal} placeholder="Journal" />
        <input className="input" name="keywords" defaultValue={keywords} placeholder="Keyword" />
        <input className="input" name="doi" defaultValue={doi} placeholder="DOI" />
        <input
          className="input"
          name="min_abstract_len"
          defaultValue={minLen}
          placeholder="Long. mínima abstract"
          inputMode="numeric"
        />
        <select className="select" name="sort" defaultValue={sort}>
          <option value="year_desc">Más recientes</option>
          <option value="year_asc">Más antiguos</option>
          <option value="abstract_len_desc">Abstract más largo</option>
          <option value="abstract_len_asc">Abstract más corto</option>
          <option value="title_asc">Título A → Z</option>
          <option value="created_desc">Orden interno</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-textSubtle">
          <input type="checkbox" name="only_embedding_valid" value="true" defaultChecked={onlyEmbedding} className="h-4 w-4 rounded border-line bg-surface-2 accent-emerald-500" />
          Solo corpus SPECTER2 (abstract &gt; 500 caracteres)
        </label>
        <div className="flex gap-2 md:col-span-2 lg:col-span-2">
          <button className="btn-primary">Aplicar filtros</button>
          <Link className="btn-ghost" href="/papers">
            Reset
          </Link>
        </div>
      </form>

      <section className="card overflow-hidden p-0">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-surface-2/40 px-5 py-3">
          <p className="text-sm text-textSubtle">
            Mostrando {visibleItems.length} de <span className="font-semibold text-textMain">{formatNumber(visibleTotal)}</span>{" "}
            resultados
          </p>
          <p className="text-xs text-textMuted">Pág. {currentPage} / {totalPages}</p>
        </header>
        <div className="scroll-x">
          <table className="table-pro">
            <thead>
              <tr>
                <th>Título</th>
                <th className="text-right">Año</th>
                <th>Journal</th>
                <th>Top PB</th>
                <th className="text-right">Abstract (chars)</th>
                <th>Embedding</th>
                <th className="text-right">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-textMuted">
                    {error ? `Error consultando la API: ${error}` : "Sin resultados con los filtros actuales."}
                  </td>
                </tr>
              )}
              {visibleItems.map((paper) => {
                const valid = paper.is_valid_for_embedding;
                return (
                  <tr key={paper.id}>
                    <td className="max-w-[420px]">
                      <p className="font-medium text-textMain leading-snug">{paper.title || "Sin título"}</p>
                      {paper.doi && (
                        <p className="mt-0.5 font-mono text-[11px] text-textMuted">DOI {paper.doi}</p>
                      )}
                    </td>
                    <td className="text-right tabular-nums text-textSubtle">{paper.year ?? "—"}</td>
                    <td className="text-textSubtle">{paper.journal ?? "—"}</td>
                    <td>
                      {paper.pb_result?.top_pb_code ? (
                        <Pill tone="accent">{paper.pb_result.top_pb_code}</Pill>
                      ) : (
                        <span className="text-textMuted">N/A</span>
                      )}
                    </td>
                    <td className="text-right tabular-nums text-textSubtle">
                      {formatNumber(paper.abstract_char_len)}
                    </td>
                    <td>
                      <Pill tone={valid ? "accent" : "warn"}>
                        {valid ? "indexado" : "fuera del índice"}
                      </Pill>
                    </td>
                    <td className="text-right">
                      <Link href={`/papers/${paper.id}`} className="text-sm text-emerald-300 hover:underline">
                        Ver →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <footer className="flex items-center justify-between border-t border-line bg-surface-2/40 px-5 py-3 text-sm">
            {currentPage > 1 ? (
              <Link href={pageLink(qs, currentPage - 1)} className="btn-ghost">
                ← Anterior
              </Link>
            ) : <span />}
            <span className="text-textMuted">Página {currentPage} de {totalPages}</span>
            {currentPage < totalPages ? (
              <Link href={pageLink(qs, currentPage + 1)} className="btn-ghost">
                Siguiente →
              </Link>
            ) : <span />}
          </footer>
        )}
      </section>
    </div>
  );
}
