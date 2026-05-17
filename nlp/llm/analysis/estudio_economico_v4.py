"""
Estudio económico — coste en tokens y consumo GPU del prompt v4 (principle-driven)
en los 3 modelos open-weight de la comparativa M2:

    - llama3.1:8b
    - qwen2.5:14b
    - gemma4:26b

Para cada (modelo, documento) registra:
    - prompt_tokens  (Ollama: prompt_eval_count)
    - output_tokens  (Ollama: eval_count)
    - durations en ns (total / load / prompt_eval / eval)
    - muestreo concurrente de nvidia-smi: power.draw (W), memory.used (MiB),
      utilization.gpu (%) — agregado en media/pico/integral energético

Salidas:
    nlp/llm/outputs/studies/estudio_economico_v4/
        per_doc.csv         filas: (modelo, doc_id, tokens, tiempos, energía)
        summary.csv         agregados por modelo
        meta.json           configuración de la corrida
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[3]
LLM_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = LLM_DIR / "outputs" / "studies" / "estudio_economico_v4"
GROUND_TRUTH_DIR = LLM_DIR / "outputs" / "ground_truth"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

MODELS = ["llama3.1:8b", "qwen2.5:14b", "gemma4:26b"]

# Tamaño de muestra por modelo. Pon None para usar todos los validados.
N_DOCS = 20

# Precio eléctrico de referencia (EUR/kWh). Ajusta si quieres otra tarifa.
PRICE_EUR_PER_KWH = 0.15

# Precios indicativos cloud por 1M tokens (USD), para comparar con APIs.
# Fuente: pricing público típico a mayo 2026. Ajusta a gusto.
CLOUD_PRICES_USD_PER_MTOK = {
    "gpt-4o":        {"input": 2.50,  "output": 10.00},
    "claude-sonnet": {"input": 3.00,  "output": 15.00},
    "claude-haiku":  {"input": 0.80,  "output": 4.00},
}
USD_EUR = 0.92  # aproximado

# ---------------------------------------------------------------------------
# Carga de corpus y reglas PB (idéntico a runners/qwen_fewshot_v4)
# ---------------------------------------------------------------------------
EXAMPLE_DOC_IDS = {"b9e1bf330baf", "9153f4dcf3d6", "f21bc832abc6"}

df_corpus = pd.read_csv(ROOT_DIR / "data" / "corpus" / "master_corpus_mixto_1000_clean_enriched.csv")
df_pbs = pd.read_csv(ROOT_DIR / "corpus_PB" / "data" / "pb_reference.csv")
df_human = pd.read_csv(GROUND_TRUTH_DIR / "validacion_real.csv", sep=";", encoding="utf-8")
ids_validados = df_human["doc_id"].dropna().astype(str).unique().tolist()

df_sample = df_corpus[df_corpus["doc_id"].isin(ids_validados)].copy()
df_sample = df_sample[~df_sample["doc_id"].isin(EXAMPLE_DOC_IDS)].copy()
if N_DOCS is not None:
    df_sample = df_sample.head(N_DOCS).copy()
print(f"Documentos a evaluar por modelo: {len(df_sample)}")

pb_rules = ""
for _, row in df_pbs.iterrows():
    pb_rules += f"- PB Code: {row['pb_code']} ({row['pb_name']})\n"
    pb_rules += f"  * Core Definition: {row['short_definition']}\n"
    pb_rules += f"  * UPV Context: Look for terms like: {row['applied_keywords_upv']}\n"
    pb_rules += f"  * ACTIVATION LOGIC: {row['activation_logic']}\n"
    pb_rules += f"  * EXCLUSION RULE (CRITICAL): {row['exclusion_notes']}\n\n"


def build_prompt_v4(abstract_text: str) -> str:
    return f"""<system_role>
You are an expert scientific evaluator analyzing research abstracts from the Universitat Politècnica de València (UPV) against the Planetary Boundaries (PBs) framework. Your judgment matters more than rigid rule-following. Use the provided framework as a reasoning aid, not a script.
</system_role>

<task>
Your goal is to identify the Planetary Boundaries that the research actually MEASURES or MODELS, strictly separating real biophysical analysis from mere background or motivational context.
</task>

<instructions>
1. Identify the operational object: the variable being measured, modelled, or experimentally manipulated.
2. Match with the PB whose Core Definition/Activation Logic fits that operational object.
3. Apply EXCLUSION RULES: purely social, legal, governance, education, philosophy or pure-software theory ⇒ "None".
4. Common confusions: aerosols/PM/AOD ⇒ PB9 (not PB1); climate alone is not PB1; biodiversity ⇒ PB7; N/P ⇒ PB4; water ⇒ PB5.
5. Reason step-by-step but output only a short summary in the JSON.
</instructions>

<reference_framework>
{pb_rules}
</reference_framework>

<calibration_cases>
- Case A: anammox bacteria + 13C isotope tracing ⇒ PB4 (nitrogen biogeochemistry measured).
- Case B: WRF forecast verification, climate is motivational ⇒ None.
- Case C: 24 mammal species response to human footprint ⇒ PB7.
Use them ONLY to calibrate judgment, do not mimic their wording.
</calibration_cases>

<input_data>
<abstract>
{abstract_text}
</abstract>
</input_data>

<constraints>
- Do NOT reuse phrases from calibration cases.
- Output ONLY valid JSON, no markdown, no greetings.
</constraints>

<output_format>
{{
    "reasoning_process": "2-3 sentence high-level summary.",
    "primary_pb": {{"pb_code": "PBX", "confidence": "High/Medium/Low"}} or null,
    "secondary_pbs": [{{"pb_code": "PBY", "confidence": "High/Medium/Low"}}],
    "rejected_pbs": ["PBZ"]
}}
</output_format>"""


# ---------------------------------------------------------------------------
# Monitor de GPU con nvidia-smi
# ---------------------------------------------------------------------------
class GpuMonitor:
    """Muestrea nvidia-smi en un hilo aparte y calcula energía consumida."""

    def __init__(self, interval_s: float = 0.25, gpu_index: int = 0):
        self.interval = interval_s
        self.gpu_index = gpu_index
        self.samples: list[tuple[float, float, float, float]] = []  # (t, P_W, mem_MiB, util_%)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.t0: float = 0.0

    def _query(self) -> tuple[float, float, float] | None:
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    f"--id={self.gpu_index}",
                    "--query-gpu=power.draw,memory.used,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=2,
            ).strip()
            p, m, u = [x.strip() for x in out.split(",")]
            return float(p), float(m), float(u)
        except Exception:
            return None

    def _run(self):
        while not self._stop.is_set():
            v = self._query()
            if v is not None:
                self.samples.append((time.time() - self.t0, *v))
            self._stop.wait(self.interval)

    def start(self):
        self.samples = []
        self.t0 = time.time()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if not self.samples:
            return {"avg_power_w": None, "peak_power_w": None,
                    "avg_mem_mib": None, "peak_mem_mib": None,
                    "avg_util_pct": None, "energy_wh": None, "n_samples": 0}
        ts = [s[0] for s in self.samples]
        ps = [s[1] for s in self.samples]
        ms = [s[2] for s in self.samples]
        us = [s[3] for s in self.samples]
        # Integral trapezoidal de potencia → energía
        energy_j = 0.0
        for i in range(1, len(self.samples)):
            dt = ts[i] - ts[i - 1]
            energy_j += 0.5 * (ps[i] + ps[i - 1]) * dt
        return {
            "avg_power_w": sum(ps) / len(ps),
            "peak_power_w": max(ps),
            "avg_mem_mib": sum(ms) / len(ms),
            "peak_mem_mib": max(ms),
            "avg_util_pct": sum(us) / len(us),
            "energy_wh": energy_j / 3600.0,
            "n_samples": len(self.samples),
        }


# ---------------------------------------------------------------------------
# Llamada a Ollama con métricas
# ---------------------------------------------------------------------------
def preflight_models():
    req = urllib.request.Request(OLLAMA_TAGS_URL)
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.load(r)
    available = {m["name"] for m in data.get("models", [])}
    missing = [m for m in MODELS if m not in available]
    if missing:
        raise RuntimeError(f"Faltan modelos en Ollama: {missing}. Descargados: {sorted(available)}")
    print(f"OK Ollama. Modelos disponibles: {sorted(available & set(MODELS))}")


def warmup(model_name: str):
    """Carga el modelo en VRAM antes de medir (no contar load_duration de la 1ª llamada)."""
    payload = {"model": model_name, "prompt": "ok", "stream": False,
               "options": {"temperature": 0.0, "num_predict": 1}}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            r.read()
    except Exception as e:
        print(f"  ! Warmup falló para {model_name}: {e}")


def call_ollama(model_name: str, prompt: str) -> dict:
    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 0.9},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            obj = json.load(r)
        wall = time.time() - t0
        return {
            "ok": True,
            "wall_s": wall,
            "response_text": obj.get("response", ""),
            "prompt_tokens": obj.get("prompt_eval_count"),
            "output_tokens": obj.get("eval_count"),
            "total_duration_ns": obj.get("total_duration"),
            "load_duration_ns": obj.get("load_duration"),
            "prompt_eval_duration_ns": obj.get("prompt_eval_duration"),
            "eval_duration_ns": obj.get("eval_duration"),
            "error": None,
        }
    except Exception as e:
        return {"ok": False, "wall_s": time.time() - t0,
                "response_text": "", "prompt_tokens": None, "output_tokens": None,
                "total_duration_ns": None, "load_duration_ns": None,
                "prompt_eval_duration_ns": None, "eval_duration_ns": None,
                "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------
def main():
    preflight_models()

    rows = []
    for model in MODELS:
        print(f"\n=== {model} ===")
        warmup(model)
        for i, (_, doc) in enumerate(df_sample.iterrows(), start=1):
            prompt = build_prompt_v4(doc["clean_abstract"])
            mon = GpuMonitor(interval_s=0.25)
            mon.start()
            res = call_ollama(model, prompt)
            gpu = mon.stop()

            row = {
                "model": model,
                "doc_id": doc["doc_id"],
                "prompt_chars": len(prompt),
                "abstract_chars": len(doc["clean_abstract"] or ""),
                **{k: res[k] for k in (
                    "ok", "wall_s", "prompt_tokens", "output_tokens",
                    "total_duration_ns", "load_duration_ns",
                    "prompt_eval_duration_ns", "eval_duration_ns", "error",
                )},
                **{f"gpu_{k}": v for k, v in gpu.items()},
            }
            rows.append(row)
            tag = "OK" if res["ok"] else "ERR"
            print(f"  [{i:3d}/{len(df_sample)}] {tag} "
                  f"prompt={res['prompt_tokens']} out={res['output_tokens']} "
                  f"wall={res['wall_s']:.2f}s "
                  f"avgP={gpu['avg_power_w'] and round(gpu['avg_power_w'],1)}W "
                  f"E={gpu['energy_wh'] and round(gpu['energy_wh'],3)}Wh")

    df = pd.DataFrame(rows)
    per_doc_path = OUTPUTS_DIR / "per_doc.csv"
    df.to_csv(per_doc_path, index=False)
    print(f"\nGuardado per-doc: {per_doc_path}")

    # ----- Resumen por modelo -----
    g = df[df["ok"]].groupby("model")
    summary = g.agg(
        n_docs=("doc_id", "count"),
        prompt_tokens_avg=("prompt_tokens", "mean"),
        prompt_tokens_total=("prompt_tokens", "sum"),
        output_tokens_avg=("output_tokens", "mean"),
        output_tokens_total=("output_tokens", "sum"),
        wall_s_avg=("wall_s", "mean"),
        wall_s_total=("wall_s", "sum"),
        avg_power_w=("gpu_avg_power_w", "mean"),
        peak_power_w=("gpu_peak_power_w", "max"),
        peak_mem_mib=("gpu_peak_mem_mib", "max"),
        energy_wh_total=("gpu_energy_wh", "sum"),
        energy_wh_avg=("gpu_energy_wh", "mean"),
    ).reset_index()

    # Coste eléctrico local
    summary["cost_eur_total_electric"] = (summary["energy_wh_total"] / 1000.0) * PRICE_EUR_PER_KWH
    summary["cost_eur_per_doc_electric"] = (summary["energy_wh_avg"] / 1000.0) * PRICE_EUR_PER_KWH

    # Coste si los mismos tokens los facturara una API cloud
    for cloud, p in CLOUD_PRICES_USD_PER_MTOK.items():
        cost_usd_per_doc = (
            summary["prompt_tokens_avg"] * p["input"] / 1_000_000
            + summary["output_tokens_avg"] * p["output"] / 1_000_000
        )
        summary[f"cost_eur_per_doc_{cloud}"] = cost_usd_per_doc * USD_EUR
        summary[f"cost_eur_total_{cloud}"] = (
            (summary["prompt_tokens_total"] * p["input"]
             + summary["output_tokens_total"] * p["output"]) / 1_000_000
        ) * USD_EUR

    summary_path = OUTPUTS_DIR / "summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Guardado resumen: {summary_path}")
    print("\n----- RESUMEN -----")
    cols = ["model", "n_docs", "prompt_tokens_avg", "output_tokens_avg",
            "wall_s_avg", "avg_power_w", "peak_mem_mib",
            "energy_wh_avg", "cost_eur_per_doc_electric"]
    print(summary[cols].to_string(index=False))

    meta = {
        "models": MODELS,
        "n_docs": int(len(df_sample)),
        "price_eur_per_kwh": PRICE_EUR_PER_KWH,
        "cloud_prices_usd_per_mtok": CLOUD_PRICES_USD_PER_MTOK,
        "usd_eur": USD_EUR,
        "ollama_url": OLLAMA_URL,
        "prompt_version": "v4_principle_driven",
    }
    (OUTPUTS_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Meta: {OUTPUTS_DIR / 'meta.json'}")


if __name__ == "__main__":
    main()
