type Props = {
  filterRule?: string;
  embeddingTextRule?: string;
  modelId?: string;
  isSpecter?: boolean;
  fallbackUsed?: boolean;
};

const FRIENDLY_FILTER = "Abstract limpio con más de 500 caracteres";
const FRIENDLY_EMBEDDING_TEXT = "Título + abstract limpio";

export function MethodologyCallout({
  modelId,
  isSpecter,
  fallbackUsed,
}: Props) {
  return (
    <aside className="surface-card relative overflow-hidden p-5">
      <div className="absolute inset-y-0 right-0 w-40 bg-emerald-radial opacity-50" />
      <div className="relative flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1.5">
          <p className="section-title text-emerald-400">Criterio metodológico</p>
          <h3 className="text-base font-semibold text-textMain">
            Filtro de calidad: <span className="text-emerald-300">{FRIENDLY_FILTER}</span>
          </h3>
          <p className="help-text">
            Cada paper se representa por <span className="text-emerald-300">{FRIENDLY_EMBEDDING_TEXT.toLowerCase()}</span>{" "}
            antes de generar el embedding. Los abstracts que tras la limpieza no superan 500 caracteres se
            descartan del índice porque no aportan contenido suficiente para una representación semántica fiable.
          </p>
        </div>
        {modelId && (
          <div className="flex items-center gap-2 text-xs text-textSubtle">
            <span className="chip-accent">{isSpecter ? "SPECTER2" : "Modelo de embeddings"}</span>
            {fallbackUsed && <span className="chip-warn">modelo alternativo</span>}
          </div>
        )}
      </div>
    </aside>
  );
}
