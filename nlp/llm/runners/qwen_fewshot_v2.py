import pandas as pd
import requests
import json
import time
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
LLM_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = LLM_DIR / 'outputs' / 'inferences'
GROUND_TRUTH_DIR = LLM_DIR / 'outputs' / 'ground_truth'
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# 1. CARGA DE DATOS Y CONSTRUCCIÓN DE REGLAS
# ==========================================
print("Cargando datasets...")
ruta_corpus = ROOT_DIR / 'data' / 'corpus' / 'master_corpus_mixto_1000_clean_enriched.csv'
ruta_pbs = ROOT_DIR / 'corpus_PB' / 'data' / 'pb_reference.csv'

# Aquí debes asegurarte de filtrar por los 208 IDs nuevos
# Si ya los tienes en un CSV nuevo, cárgalo aquí. Por ahora, asumo que 
# sustituyes 'ids_validados' por tu lista real de 208 IDs.

try:
    df_corpus = pd.read_csv(ruta_corpus)
    df_pbs = pd.read_csv(ruta_pbs)
except FileNotFoundError as e:
    print(f"Error fatal: No se encontró el archivo. {e}")
    exit()

# Lista de doc_ids leída desde el ground truth (única fuente de verdad).
df_human = pd.read_csv(GROUND_TRUTH_DIR / 'validacion_real.csv', sep=';', encoding='utf-8')
ids_validados = df_human['doc_id'].dropna().astype(str).unique().tolist()
df_sample = df_corpus[df_corpus['doc_id'].isin(ids_validados)].copy()
print(f"✅ Filtro aplicado: Se van a analizar exactamente {len(df_sample)} papers validados.")

pb_rules = ""
for index, row in df_pbs.iterrows():
    pb_rules += f"- PB Code: {row['pb_code']} ({row['pb_name']})\n"
    pb_rules += f"  * Core Definition: {row['short_definition']}\n"
    pb_rules += f"  * UPV Context: Look for terms like: {row['applied_keywords_upv']}\n"
    pb_rules += f"  * ACTIVATION LOGIC: {row['activation_logic']}\n"
    pb_rules += f"  * EXCLUSION RULE (CRITICAL): {row['exclusion_notes']}\n\n"

# ==========================================
# 2. CONFIGURACIÓN DEL LLM LOCAL (OLLAMA)
# ==========================================
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:14b" # O el modelo que decidáis usar como baseline

def classify_abstract_few_shot(abstract_text):
    # =========================================================================
    # PROMPT v2: ZERO-SHOT CoT CON ALGORITMO DEDUCTIVO GUIADO
    # Sustituye al Few-Shot Contrastivo v1, que provocaba:
    #   - Efecto "Loro": el modelo copiaba literalmente frases de los Examples.
    #   - Colapso de PB7: recall 23% -> 0% por regla espuria aprendida.
    #   - Trampa Social: rechazo excesivo como "político/económico".
    # Estrategia: eliminar ejemplos prefabricados, forzar checklist analítico
    # paso a paso sobre el documento real (cf. problema_few_shot.pdf §3).
    # =========================================================================

    prompt = f"""You are a strict scientific evaluator analyzing research abstracts from the Universitat Politècnica de València (UPV) against the Planetary Boundaries (PBs) framework.

Your task: identify the Planetary Boundaries that the research actually measures or models.

### PLANETARY BOUNDARIES RULES:
{pb_rules}

### YOUR ANALYTICAL ALGORITHM (mandatory deductive checklist)

Execute these steps internally, in order, ON THE REAL TEXT BELOW. Do not invent metrics that are not in the abstract. Do not reuse rhetoric from these instructions in your output.

Step 1 — BIOPHYSICAL EXTRACTION
   List every explicit physical, chemical, biological, ecological or environmental metric, variable, model, sample, dataset or measurement that appears in the abstract. Quote them.
   - If the list is EMPTY (the paper is purely socio-economic, governance, pure policy, education, finance, ethics or qualitative survey with no biophysical observation), the verdict is "None" and you skip to Step 5.
   - The presence of a biophysical metric, even inside an applied/engineering/socio-environmental study, is sufficient to continue.

Step 2 — CANDIDATE MAPPING
   For EACH extracted metric, map it to the PB whose Core Definition / Activation Logic it triggers. A paper can map to several PBs.
   - Biosphere/ecological responses (species, biodiversity, ecosystems, phenology, fungi, fauna, vegetation, soil biota) → PB7 is a legitimate PRIMARY candidate, not just a side effect of PB1.
   - Particulate matter, PM2.5, PM10, aerosols, AOD, black carbon → PB9 (atmospheric aerosol loading), NOT PB1.
   - "Climate" or "warming" alone is NOT enough for PB1: require an explicit climate driver (GHG, radiative forcing, temperature trend, climate scenario, climate adaptation/impact study).
   - Nutrients (N, P, fertilizers, eutrophication) → PB4. Water quantity/quality, freshwater use → PB5. If the study touches both, pick the one that is the MATHEMATICAL focus (the variable being modelled or measured), not the contextual one.

Step 3 — EXCLUSION CHECK
   For every candidate PB from Step 2, apply its EXCLUSION RULE. Discard any PB whose exclusion rule is explicitly violated.
   - "Socio-economic" rejection is ONLY valid when there is NO biophysical metric in Step 1. If Step 1 found valid metrics, you may NOT reject the paper as merely "political or economic". A document with PB4 or PB8 metrics is a PB4/PB8 paper even if it also mentions policy.

Step 4 — HIERARCHY
   Among the surviving PBs, select as `primary_pb` the boundary that is the dominant analytical focus (the one being measured/modelled, not the one merely mentioned as context). Any other surviving PB goes to `secondary_pbs`. PBs discarded in Step 3 go to `rejected_pbs`.

Step 5 — OUTPUT
   Write `reasoning_process` as a concise factual trace of Steps 1–4 referring to the actual text. Do NOT echo phrases from these instructions (e.g. "anti-overfiltering", "I must not over-reject", "applying the exclusion rule"). Quote the abstract's own terms.

### ABSTRACT TO EVALUATE:
<text>
{abstract_text}
</text>

### OUTPUT FORMAT
Output ONLY valid JSON matching this exact schema, no markdown, no extra text:

{{
    "reasoning_process": "Step1 metrics found: [...]. Step2 candidates: [...]. Step3 exclusions: [...]. Step4 dominant focus: [...].",
    "primary_pb": {{"pb_code": "PBX", "confidence": "High/Medium/Low"}} or null,
    "secondary_pbs": [{{"pb_code": "PBY", "confidence": "High/Medium/Low"}}],
    "rejected_pbs": ["PBZ"]
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json", # Garantiza que el output no se rompa en Python
        "stream": False,
        "options": {
            "temperature": 0.0, # Crítico para mantener la precisión
            "top_p": 0.9
        }
    }

    start_time = time.time()
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        result_json = response.json()
        return result_json.get("response", "{}"), time.time() - start_time
    except Exception as e:
        return json.dumps({"error": str(e)}), time.time() - start_time
    
# ==========================================
# 3. EXTRAE EL JSON Y SEPARA LAS COLUMNAS
# ==========================================
def parse_llm_output(raw_text):
    try:
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            data = json.loads(raw_text[start_idx:end_idx+1])
        else:
            raise ValueError("No JSON structure found.")
        
        reasoning = data.get("reasoning_process", "")
        
        prim_pb = data.get("primary_pb")
        if prim_pb and isinstance(prim_pb, dict):
            prim_code = prim_pb.get("pb_code", "None")
            prim_conf = prim_pb.get("confidence", "Unknown")
        else:
            prim_code, prim_conf = "None", "N/A"
            
        sec_pbs = data.get("secondary_pbs", [])
        if sec_pbs and isinstance(sec_pbs, list):
            sec_codes = ", ".join([item.get("pb_code", "") for item in sec_pbs if isinstance(item, dict)])
        else:
            sec_codes = "None"
            
        rej_pbs = data.get("rejected_pbs", [])
        if rej_pbs and isinstance(rej_pbs, list):
            rej_codes = ", ".join(rej_pbs)
        else:
            rej_codes = "None"

        return reasoning, prim_code, prim_conf, sec_codes, rej_codes
        
    except Exception as e:
        return f"Error: {e}", "Error", "Error", "Error", "Error"

# ==========================================
# 4. BUCLE DE EVALUACIÓN FEWSHOT
# ==========================================
total_papers = len(df_sample)
# v2: estrategia Zero-Shot CoT con algoritmo deductivo guiado
# (sustituye al prompt Few-Shot Contrastivo v1 que generó el efecto loro).
output_filename = OUTPUTS_DIR / 'qwen2.5_14b_fewshot_v2.csv'

if os.path.exists(output_filename):
    os.remove(output_filename)

print(f"\nIniciando evaluación FEWSHOT v2 (Zero-Shot CoT guiado) con modelo: {MODEL_NAME}")
print("-" * 70)

for i, (index, row) in enumerate(df_sample.iterrows(), start=1):
    print(f"[{i}/{total_papers}] Doc: {row['doc_id']}...", end=" ", flush=True)
    
    llm_out, t_elapsed = classify_abstract_few_shot(row['clean_abstract'])
    reasoning, p_code, p_conf, s_codes, r_codes = parse_llm_output(llm_out)
    
    print(f"[{t_elapsed:.1f}s] Pri: {p_code} | Sec: {s_codes} | Rej: {r_codes}")
    
    df_fila = pd.DataFrame([{
        'doc_id': row['doc_id'],
        'llm_primary_pb': p_code,
        'llm_primary_conf': p_conf,
        'llm_secondary_pbs': s_codes,
        'llm_rejected_pbs': r_codes,
        'llm_reasoning': reasoning,
        'inference_time_sec': t_elapsed
    }])
    
    if not os.path.isfile(output_filename):
        df_fila.to_csv(output_filename, index=False)
    else:
        df_fila.to_csv(output_filename, mode='a', header=False, index=False)

print("\n" + "=" * 70)
print(f"✅ Finalizado. Dataset FEWSHOT guardado en: {output_filename}")