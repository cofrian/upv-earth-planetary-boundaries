type Step = {
  index: string;
  title: string;
  detail: string;
  badge: string;
};

const STEPS: Step[] = [
  {
    index: "01",
    title: "Detección y normalización del abstract",
    detail:
      "Se extrae el abstract del PDF, se normaliza Unicode (NFKC), se eliminan caracteres de control y se compactan saltos de línea y espacios redundantes.",
    badge: "raw → normalizado",
  },
  {
    index: "02",
    title: "Filtro lingüístico y dedupe",
    detail:
      "Se descartan documentos sin abstract útil, en idioma distinto al inglés (langid con confianza > 0.6) o duplicados por DOI o por similitud de título.",
    badge: "idioma + duplicados",
  },
  {
    index: "03",
    title: "Limpieza semántica para embedding",
    detail:
      "Se eliminan URLs, emails, citas tipo (Author, 2020), referencias numéricas, símbolos de copyright, ruido bibliográfico y secciones residuales (Acknowledgements, Funding, References).",
    badge: "URLs · citas · ruido",
  },
  {
    index: "04",
    title: "Filtro metodológico de calidad",
    detail:
      "Solo entran al corpus SPECTER2 los abstracts cuyo texto limpio supera 500 caracteres. Por debajo de ese umbral la representación semántica es poco fiable.",
    badge: "abstract limpio > 500",
  },
  {
    index: "05",
    title: "Representación final del paper",
    detail:
      "Cada paper se compone como “título + abstract limpio”. Esa cadena alimenta el tokenizador de SPECTER2 y se trunca a 512 tokens (límite duro del modelo).",
    badge: "título + abstract limpio",
  },
  {
    index: "06",
    title: "Embedding y normalización del vector",
    detail:
      "Se calcula el embedding con SPECTER2 (768 dimensiones), se aplica L2-normalize y se persiste en el índice de similitud por contenido.",
    badge: "SPECTER2 · 768d · L2",
  },
];

export function CleaningPipelineCard() {
  return (
    <article className="card space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <p className="section-title">Preparación del texto para SPECTER2</p>
          <h3 className="text-lg font-semibold text-textMain">
            Limpieza aplicada antes de generar el embedding
          </h3>
          <p className="help-text max-w-3xl">
            SPECTER2 espera entradas científicas cortas y bien formadas (≤ 512 tokens). Esta es la
            secuencia exacta que aplica el pipeline para que cada paper llegue al modelo en igualdad
            de condiciones y sin ruido bibliográfico.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="chip">entrada: PDF / metadatos</span>
          <span className="chip-accent">salida: vector 768d</span>
        </div>
      </header>

      <ol className="grid gap-3 md:grid-cols-2">
        {STEPS.map((step) => (
          <li
            key={step.index}
            className="rounded-2xl border border-line bg-surface-2 p-4 transition hover:border-emerald-500/40"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-300">
                {step.index}
              </span>
              <span className="chip">{step.badge}</span>
            </div>
            <p className="mt-2 text-sm font-semibold text-textMain">{step.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-textSubtle">{step.detail}</p>
          </li>
        ))}
      </ol>

      <footer className="flex flex-wrap items-center gap-2 border-t border-line/60 pt-3 text-xs text-textMuted">
        <span className="chip">criterio: abstract limpio &gt; 500 caracteres</span>
        <span className="chip">representación: título + abstract limpio</span>
        <span className="chip">truncado: 512 tokens (SPECTER2)</span>
      </footer>
    </article>
  );
}
