import { AbstractValidation, EmbeddingInfo } from "@/lib/types";
import { formatNumber, modelLabel } from "./format";

type Props = {
  validation: AbstractValidation | null;
  embedding: EmbeddingInfo | null;
};

function Row({ label, value, ok }: { label: string; value: string; ok: boolean | "warn" }) {
  const badge = ok === true ? "chip-accent" : ok === "warn" ? "chip-warn" : "chip-danger";
  const text = ok === true ? "OK" : ok === "warn" ? "atención" : "fallo";
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-surface-2 px-4 py-3">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-textMuted">{label}</p>
        <p className="mt-1 text-sm font-semibold text-textMain">{value}</p>
      </div>
      <span className={badge}>{text}</span>
    </div>
  );
}

export function AbstractValidationCard({ validation, embedding }: Props) {
  if (!validation && !embedding) {
    return (
      <section className="card">
        <p className="section-title">Validación metodológica</p>
        <p className="mt-2 text-sm text-textMuted">
          Aún no se ha procesado el paper. La validación aparecerá cuando el pipeline complete la extracción del
          abstract.
        </p>
      </section>
    );
  }

  const detected = validation ? validation.abstract_detected : false;
  const passes = validation ? validation.passes_threshold : false;
  const valid = validation ? validation.is_valid_for_embedding : false;
  const embeddingDim = embedding?.embedding_dim;

  return (
    <section className="card space-y-4">
      <header className="space-y-1">
        <p className="section-title">Criterio metodológico</p>
        <h3 className="text-lg font-semibold text-textMain">Validación del abstract y embedding</h3>
        <p className="help-text">
          La plataforma exige que el abstract limpio supere 500 caracteres y representa cada paper como{" "}
          <span className="text-emerald-300">título + abstract limpio</span> antes de generar el embedding. Los
          que no cumplen el criterio se mantienen en el corpus válido pero quedan fuera del índice de similitud.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-2">
        <Row
          label="Abstract detectado"
          value={detected ? "Detectado correctamente" : "No detectado"}
          ok={detected ? true : false}
        />
        <Row
          label="Longitud del abstract"
          value={`${formatNumber(validation?.abstract_char_len ?? 0)} caracteres`}
          ok={passes ? true : "warn"}
        />
        <Row
          label="Supera 500 caracteres"
          value={passes ? "Sí · cumple el criterio" : "No · descartado del índice"}
          ok={passes}
        />
        <Row
          label="Apto para SPECTER2"
          value={valid ? "Entra al índice de similitud" : "Fuera del índice"}
          ok={valid}
        />
      </div>

      {embedding && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <p className="section-title text-emerald-300">Embedding generado</p>
              <h4 className="mt-1 flex flex-wrap items-center gap-2 text-base font-semibold text-textMain">
                <span>{modelLabel(embedding.model_id)}</span>
                {embedding.fallback_used && (
                  <span className="chip-warn">modelo alternativo (fallback)</span>
                )}
              </h4>
            </div>
            <div className="flex flex-wrap gap-1.5 text-xs">
              <span className="chip">dimensión {embeddingDim || "—"}</span>
              <span className="chip">título + abstract limpio</span>
            </div>
          </div>
          {embedding.embedding_text_preview && (
            <p className="mt-3 text-xs leading-relaxed text-textSubtle">
              <span className="text-textMuted">Vista previa del texto embebido:</span>{" "}
              {embedding.embedding_text_preview}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
