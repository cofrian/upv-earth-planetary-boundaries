import { KpiCard } from "@/components/KpiCard";
import { formatNumber, formatPercent } from "@/components/format";
import { apiGet } from "@/lib/api";
import { ModelsBenchmark } from "@/lib/benchmark-types";

const FALLBACK: ModelsBenchmark = {
  available: false,
  n_papers: 0,
  models: [],
  per_pb: [],
  agreement: { both_correct: 0, only_specter: 0, only_scibert: 0, both_wrong: 0 },
  discordance_examples: { only_specter: [], only_scibert: [] },
  backbones_table: [],
  human_validation: { available: false },
};

async function safe(): Promise<ModelsBenchmark> {
  try {
    return await apiGet<ModelsBenchmark>("/analytics/models-benchmark");
  } catch {
    return FALLBACK;
  }
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function pbBar({ pb, label, value, total }: { pb: string; label: string; value: number; total: number }) {
  const pctValue = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-10 font-mono text-textSubtle">{pb}</span>
      <span className="w-24 text-textMuted">{label}</span>
      <div className="flex-1 overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-2.5 rounded-full"
          style={{
            width: `${pctValue}%`,
            background: "linear-gradient(90deg,#34d399,#10b981)",
          }}
        />
      </div>
      <span className="w-12 text-right font-mono text-textMain">{pctValue.toFixed(1)}%</span>
      <span className="w-16 text-right text-[10px] text-textMuted">
        {value}/{total}
      </span>
    </div>
  );
}

export default async function BenchmarkPage() {
  const data = await safe();

  if (!data.available) {
    return (
      <div className="card p-8 text-center text-sm text-textMuted">
        No hay datos de benchmark disponibles. Genera el CSV de comparación con el script
        <code className="mx-1 rounded bg-surface-2 px-1.5 py-0.5">scripts/recompute_models_comparison.py</code>
        y vuelve a cargar.
      </div>
    );
  }

  const specter = data.models.find((m) => m.model === "SPECTER2");
  const scibert = data.models.find((m) => m.model === "SciBERT");

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <span className="chip-accent">Benchmark · Clasificación PB</span>
        <h1 className="text-3xl font-semibold tracking-tight text-balance lg:text-4xl">
          SPECTER2 vs SciBERT
        </h1>
        <p className="max-w-3xl text-base leading-relaxed text-textSubtle">
          Comparativa real sobre los {formatNumber(data.n_papers)} papers indexados del corpus. La verdad
          de referencia es la organización en carpetas del drive UPV ({data.ground_truth || "pb_folder"}),
          que actúa como pseudo-ground-truth: cada paper estaba físicamente en la carpeta del PB principal
          que el equipo le asignó.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="SPECTER2 · top-1"
          value={specter ? Math.round(specter.top1_accuracy * 1000) / 10 : 0}
          valueFormat="raw"
          helperBadge={specter ? `${specter.top1_correct}/${data.n_papers}` : "—"}
          helperTone="accent"
          helper="Acierta el PB principal a la primera"
          highlight
        />
        <KpiCard
          label="SciBERT · top-1"
          value={scibert ? Math.round(scibert.top1_accuracy * 1000) / 10 : 0}
          valueFormat="raw"
          helperBadge={scibert ? `${scibert.top1_correct}/${data.n_papers}` : "—"}
          helper="Acierta el PB principal a la primera"
        />
        <KpiCard
          label="SPECTER2 · top-1 ó top-2"
          value={specter ? Math.round(specter.top2_accuracy * 1000) / 10 : 0}
          valueFormat="raw"
          helperBadge={specter ? `${specter.top2_correct}/${data.n_papers}` : "—"}
          helper="El PB correcto está entre los 2 más probables"
        />
        <KpiCard
          label="SciBERT · top-1 ó top-2"
          value={scibert ? Math.round(scibert.top2_accuracy * 1000) / 10 : 0}
          valueFormat="raw"
          helperBadge={scibert ? `${scibert.top2_correct}/${data.n_papers}` : "—"}
          helper="El PB correcto está entre los 2 más probables"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="card space-y-4">
          <header>
            <p className="section-title">Cruce de aciertos</p>
            <h3 className="text-lg font-semibold">¿En qué papers coinciden los dos modelos?</h3>
          </header>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-4 py-3">
              <span className="text-textSubtle">Ambos modelos aciertan</span>
              <span className="chip-accent">{data.agreement.both_correct}</span>
            </li>
            <li className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-4 py-3">
              <span className="text-textSubtle">Solo SPECTER2 acierta</span>
              <span className="chip">{data.agreement.only_specter}</span>
            </li>
            <li className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-4 py-3">
              <span className="text-textSubtle">Solo SciBERT acierta</span>
              <span className="chip">{data.agreement.only_scibert}</span>
            </li>
            <li className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-4 py-3">
              <span className="text-textSubtle">Ambos fallan</span>
              <span className="chip-warn">{data.agreement.both_wrong}</span>
            </li>
          </ul>
          <p className="help-text border-t border-line/60 pt-3">
            La gran zona de "ambos fallan" no es ruido del modelo: es la dificultad real de la tarea (papers
            multi-PB y solapamiento temático entre boundaries).
          </p>
        </article>

        <article className="card space-y-4">
          <header>
            <p className="section-title">Métricas por backbone (oficiales)</p>
            <h3 className="text-lg font-semibold">Tabla de [backbone_comparison.csv]</h3>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-textMuted">
                <tr className="border-b border-line/60">
                  <th className="py-2 pr-3 text-left">Modelo</th>
                  <th className="py-2 pr-3 text-left">Modo</th>
                  <th className="py-2 pr-3 text-right">micro-F1</th>
                  <th className="py-2 pr-3 text-right">macro-F1</th>
                  <th className="py-2 text-right">LRAP</th>
                </tr>
              </thead>
              <tbody>
                {data.backbones_table.map((row, idx) => (
                  <tr key={`${row.model}-${row.mode}-${idx}`} className="border-b border-line/30">
                    <td className="py-1.5 pr-3 font-mono text-textMain">{row.model}</td>
                    <td className="py-1.5 pr-3 text-textSubtle">{row.mode}</td>
                    <td className="py-1.5 pr-3 text-right font-mono">{row.micro_f1.toFixed(3)}</td>
                    <td className="py-1.5 pr-3 text-right font-mono">{row.macro_f1.toFixed(3)}</td>
                    <td className="py-1.5 text-right font-mono">{row.lrap.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="help-text border-t border-line/60 pt-3">
            Métricas precalculadas en el benchmark de backbones BERT-family. SPECTER2 no está aquí: las
            métricas SPECTER vs SciBERT del bloque superior se calculan al vuelo cruzando precomputados.
          </p>
        </article>
      </section>

      <section className="card space-y-4">
        <header>
          <p className="section-title">Accuracy top-1 por Planetary Boundary</p>
          <h3 className="text-lg font-semibold">¿En qué PBs gana cada modelo?</h3>
        </header>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.16em] text-emerald-300">SPECTER2</p>
            {data.per_pb.map((row) => (
              <div key={`sp-${row.pb_code}`}>
                {pbBar({ pb: row.pb_code, label: "", value: Math.round(row.specter_top1 * row.n), total: row.n })}
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.16em] text-emerald-300">SciBERT</p>
            {data.per_pb.map((row) => (
              <div key={`sc-${row.pb_code}`}>
                {pbBar({ pb: row.pb_code, label: "", value: Math.round(row.scibert_top1 * row.n), total: row.n })}
              </div>
            ))}
          </div>
        </div>
        <p className="help-text border-t border-line/60 pt-3">
          SPECTER2 destaca en boundaries con vocabulario científico muy específico (PB2 acidificación oceánica,
          PB9 aerosoles atmosféricos). SciBERT gana en PB1 (clima) y PB6 (uso del suelo) porque tiene vocabulario
          contextual aprendido en fine-tuning.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="card space-y-4">
          <header>
            <p className="section-title">Ejemplos donde solo SPECTER2 acierta</p>
            <h3 className="text-base font-semibold">Top-{data.discordance_examples.only_specter.length} por similitud</h3>
          </header>
          <ul className="space-y-2 text-xs">
            {data.discordance_examples.only_specter.map((ex) => (
              <li key={ex.doc_id} className="rounded-xl border border-line bg-surface-2 p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-mono text-textMain">{ex.doc_id}</span>
                  <span className="chip-accent">SPECTER {pct(ex.specter_score)}</span>
                </div>
                <p className="mt-1 text-textSubtle">
                  Verdad: <span className="font-mono text-emerald-300">{ex.gt}</span> · SPECTER:{" "}
                  <span className="font-mono text-emerald-300">{ex.specter_pred}</span> · SciBERT:{" "}
                  <span className="font-mono text-amber-300">{ex.scibert_pred}</span>
                </p>
              </li>
            ))}
          </ul>
        </article>
        <article className="card space-y-4">
          <header>
            <p className="section-title">Ejemplos donde solo SciBERT acierta</p>
            <h3 className="text-base font-semibold">Top-{data.discordance_examples.only_scibert.length} por similitud baja de SPECTER</h3>
          </header>
          <ul className="space-y-2 text-xs">
            {data.discordance_examples.only_scibert.map((ex) => (
              <li key={ex.doc_id} className="rounded-xl border border-line bg-surface-2 p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-mono text-textMain">{ex.doc_id}</span>
                  <span className="chip">SPECTER {pct(ex.specter_score)}</span>
                </div>
                <p className="mt-1 text-textSubtle">
                  Verdad: <span className="font-mono text-emerald-300">{ex.gt}</span> · SPECTER:{" "}
                  <span className="font-mono text-amber-300">{ex.specter_pred}</span> · SciBERT:{" "}
                  <span className="font-mono text-emerald-300">{ex.scibert_pred}</span>
                </p>
              </li>
            ))}
          </ul>
        </article>
      </section>

      {data.human_validation.available && (
        <section className="space-y-4">
          <header className="space-y-2">
            <span className="chip-accent">Validación humana</span>
            <h2 className="text-2xl font-semibold tracking-tight">
              Aciertos contra etiquetas anotadas a mano ({data.human_validation.n_papers_total} papers)
            </h2>
            <p className="max-w-3xl text-sm text-textSubtle">
              Cruce de SPECTER2 y SciBERT contra las etiquetas humanas multi-label de
              <code className="mx-1 rounded bg-surface-2 px-1 py-0.5 text-xs">validacion_real.csv</code>.
              Cada paper tiene en media{" "}
              <span className="text-emerald-300">
                {data.human_validation.avg_gold_labels_per_paper.toFixed(2)} PBs
              </span>{" "}
              etiquetados (1stpb, 2ndpb, 3rdpb). Un acierto se cuenta cuando la predicción del modelo
              está dentro del conjunto humano.
            </p>
          </header>

          <article className="card space-y-3">
            <header>
              <p className="section-title">Cobertura de la evaluación</p>
              <h3 className="text-base font-semibold">¿Sobre cuántos papers podemos comparar realmente?</h3>
            </header>
            <div className="grid gap-2 md:grid-cols-4 text-sm">
              <div className="rounded-xl border border-line bg-surface-2 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-textMuted">Anotados a mano</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.n_papers_total}
                </p>
                <p className="text-[10px] text-textMuted">total con 1stpb</p>
              </div>
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-emerald-300">SPECTER puede evaluar</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.n_specter_evaluated}
                </p>
                <p className="text-[10px] text-textMuted">índice + recuperados al vuelo</p>
              </div>
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-emerald-300">SciBERT puede evaluar</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.n_scibert_evaluated}
                </p>
                <p className="text-[10px] text-textMuted">predictions_all_docs.csv</p>
              </div>
              <div className="rounded-xl border border-line bg-surface-2 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-textMuted">Ambos en común</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.n_both_evaluated}
                </p>
                <p className="text-[10px] text-textMuted">papers que sí están en los dos</p>
              </div>
            </div>
            <p className="help-text border-t border-line/60 pt-3">
              Los papers anotados que ningún modelo cubre son artículos que ya no están en el corpus actual
              (eliminados durante la limpieza o pertenecientes a versiones anteriores del muestreo). Las
              métricas siguientes se calculan sobre el conjunto evaluable de cada modelo, no sobre el
              total.
            </p>
          </article>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data.human_validation.models.map((m) => (
              <KpiCard
                key={`hum-${m.model}`}
                label={`${m.model} · top-1 ∈ gold`}
                value={Math.round(m.top1_in_gold_accuracy * 1000) / 10}
                valueFormat="raw"
                helperBadge={`${m.top1_in_gold_correct}/${m.n_evaluated}`}
                helperTone={m.model === "SPECTER2" ? "accent" : "neutral"}
                helper="El top-1 está entre los PBs anotados a mano"
                highlight={m.model === "SPECTER2"}
              />
            ))}
            {data.human_validation.models.map((m) => (
              <KpiCard
                key={`hum-top12-${m.model}`}
                label={`${m.model} · top1+top2 ∈ gold`}
                value={Math.round(m.top12_in_gold_accuracy * 1000) / 10}
                valueFormat="raw"
                helperBadge={`${m.top12_in_gold_correct}/${m.n_evaluated}`}
                helper="Alguno de los dos primeros está en el gold"
              />
            ))}
          </div>

          <article className="card space-y-3">
            <header className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <p className="section-title">Cruce top-1 · n = {data.human_validation.agreement.n_paired}</p>
                <h3 className="text-base font-semibold">¿Quién acierta y quién no?</h3>
              </div>
              <span className="chip">solo papers que ambos pueden predecir</span>
            </header>
            <div className="grid gap-2 md:grid-cols-4 text-sm">
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-emerald-300">Ambos OK</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.agreement.both_top1_correct}
                </p>
              </div>
              <div className="rounded-xl border border-line bg-surface-2 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-textMuted">Solo SPECTER</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.agreement.only_specter_top1}
                </p>
              </div>
              <div className="rounded-xl border border-line bg-surface-2 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-textMuted">Solo SciBERT</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.agreement.only_scibert_top1}
                </p>
              </div>
              <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.16em] text-amber-300">Ambos fallan</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {data.human_validation.agreement.both_top1_wrong}
                </p>
              </div>
            </div>
          </article>

          <article className="card space-y-3">
            <header>
              <p className="section-title">Ejemplos · top scores SPECTER2</p>
              <h3 className="text-base font-semibold">Cómo se compara cada modelo paper a paper</h3>
            </header>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-textMuted">
                  <tr className="border-b border-line/60">
                    <th className="py-2 pr-3 text-left">doc_id</th>
                    <th className="py-2 pr-3 text-left">Gold (humano)</th>
                    <th className="py-2 pr-3 text-left">SPECTER pred</th>
                    <th className="py-2 pr-3 text-left">SciBERT pred</th>
                    <th className="py-2 pr-3 text-right">SPECTER score</th>
                    <th className="py-2 text-center">SP/SC</th>
                  </tr>
                </thead>
                <tbody>
                  {data.human_validation.examples.map((ex) => (
                    <tr key={ex.doc_id} className="border-b border-line/30">
                      <td className="py-1.5 pr-3 font-mono text-textMain">{ex.doc_id}</td>
                      <td className="py-1.5 pr-3 font-mono text-emerald-300">{ex.gold}</td>
                      <td
                        className={`py-1.5 pr-3 font-mono ${
                          ex.specter_ok ? "text-emerald-300" : "text-amber-300"
                        }`}
                      >
                        {ex.specter_pred}
                      </td>
                      <td
                        className={`py-1.5 pr-3 font-mono ${
                          ex.scibert_ok ? "text-emerald-300" : "text-amber-300"
                        }`}
                      >
                        {ex.scibert_pred}
                      </td>
                      <td className="py-1.5 pr-3 text-right font-mono">{(ex.specter_score * 100).toFixed(1)}%</td>
                      <td className="py-1.5 text-center font-mono">
                        {ex.specter_ok ? "✓" : "✗"} / {ex.scibert_ok ? "✓" : "✗"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="help-text border-t border-line/60 pt-3">
              Verde = predicción dentro del conjunto humano. Ámbar = fuera. Las etiquetas humanas pueden ser
              múltiples; basta con acertar uno de los PBs anotados.
            </p>
          </article>
        </section>
      )}

      <section className="card space-y-3 text-xs text-textMuted">
        <p className="section-title">Notas metodológicas</p>
        <ul className="list-disc space-y-1 pl-5 leading-relaxed">
          <li>
            <strong>SPECTER2</strong> es zero-shot: no se entrena con etiquetas PB. Cada paper se compara por
            similitud coseno contra el texto representativo de cada PB del catálogo curado por UPV.
          </li>
          <li>
            <strong>SciBERT</strong> es supervisado: clasificador multi-label entrenado sobre embeddings SciBERT
            con regla <code>threshold + delta</code> ajustada en validación.
          </li>
          <li>
            La "verdad" es la organización en carpetas del drive UPV. No es una validación humana estricta —
            puede haber papers mal organizados. Para validación humana real (108 papers) consulta el corpus en
            <code className="mx-1 rounded bg-surface-2 px-1.5 py-0.5">nlp/llm/outputs/ground_truth/validacion_real.csv</code>.
          </li>
          <li>
            Se evalúa <strong>top-1</strong> (etiqueta única) aunque muchos papers son multilabel reales.
            Por eso SciBERT con <code>top-2</code> y <code>threshold_delta</code> sube a {formatPercent((scibert?.top2_accuracy ?? 0) * 100)}.
          </li>
        </ul>
      </section>
    </div>
  );
}
