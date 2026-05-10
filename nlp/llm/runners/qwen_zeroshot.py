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

def classify_abstract_zero_shot(abstract_text):
    # PROMPT MAESTRO ZERO-SHOT: Estructura jerárquica + Anti-Overfiltering
    prompt = f"""You are a strict and precise scientific evaluator analyzing research abstracts from the Universitat Politècnica de València (UPV) against the Planetary Boundaries (PBs) framework.

Your task is to identify the Planetary Boundaries affected by the research. You must strictly apply the activation rules and evaluate the exclusion rules. 

CRITICAL GUARDRAILS:
1. Do not force a match if the scientific connection is weak, purely theoretical, or merely thematic.
2. Conversely, do not over-reject if the explicit biophysical metric is present.

### PLANETARY BOUNDARIES RULES:
{pb_rules}

### ABSTRACT TO EVALUATE:
<text>
{abstract_text}
</text>

### INSTRUCTIONS (ZERO-SHOT):
Step 1: Concept Extraction. Identify the core scientific metrics, biophysical impacts, and specific chemical/physical substances measured in the abstract.
Step 2: Exclusion Check (CRITICAL). Apply the EXCLUSION RULE for every PB you consider. If the rule is explicitly violated (e.g., social sciences without biophysical metrics), the PB MUST be discarded into "rejected_pbs".
Step 3: Anti-Overfiltering Clause. DO NOT OVER-REJECT. If the abstract explicitly measures, models, or analyzes the exact physical metrics of a boundary (e.g., measuring "aerosols" or "PM2.5" for PB9, "pH" for PB2, or "nitrogen/phosphorus" for PB4), you MUST assign that PB, even if the broader context is applied research (like air quality, wastewater management, or engineering).
Step 4: Similarity Matching & Hierarchy. From the surviving PBs, assign the SINGLE most dominant Planetary Boundary as the "primary_pb". If other boundaries are explicitly and strongly affected, list them as "secondary_pbs".
Step 5: JSON Output. Output ONLY valid JSON matching this exact schema. Do not include markdown blocks or extra text:

{{
    "reasoning_process": "Analyze the biophysical metrics, weigh the exclusion rules against the anti-overfiltering clause, and scientifically justify your primary, secondary, and rejected PBs.",
    "primary_pb": {{"pb_code": "PBX", "confidence": "High/Medium/Low"}} or null,
    "secondary_pbs": [{{"pb_code": "PBY", "confidence": "High/Medium/Low"}}],
    "rejected_pbs": ["PBZ", "PBW"]
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json", # Garantiza que Ollama devuelva un JSON perfectamente parseable
        "stream": False,
        "options": {
            "temperature": 0.0, # Vital para que sea determinista y analítico
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
# 4. BUCLE DE EVALUACIÓN ZERO-SHOT
# ==========================================
total_papers = len(df_sample)
output_filename = OUTPUTS_DIR / 'qwen2.5_14b_zeroshot.csv'

if os.path.exists(output_filename):
    os.remove(output_filename)

print(f"\nIniciando evaluación ZERO-SHOT MULTI-LABEL con modelo: {MODEL_NAME}")
print("-" * 70)

for i, (index, row) in enumerate(df_sample.iterrows(), start=1):
    print(f"[{i}/{total_papers}] Doc: {row['doc_id']}...", end=" ", flush=True)
    
    llm_out, t_elapsed = classify_abstract_zero_shot(row['clean_abstract'])
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
print(f"✅ Finalizado. Dataset ZERO-SHOT guardado en: {output_filename}")