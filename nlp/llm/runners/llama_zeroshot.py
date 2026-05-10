import pandas as pd
import requests
import json
import time
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = SCRIPT_DIR / 'outputs'
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# 1. CARGA DE DATOS Y CONSTRUCCIÓN DE REGLAS
# ==========================================
print("Cargando datasets...")
# Rutas a tus archivos en la máquina virtual
ruta_corpus = ROOT_DIR / 'data' / 'corpus' / 'master_corpus_mixto_1000_clean_enriched.csv'
ruta_pbs = ROOT_DIR / 'corpus_PB' / 'data' / 'pb_reference.csv'

try:
    df_corpus = pd.read_csv(ruta_corpus)
    df_pbs = pd.read_csv(ruta_pbs)
except FileNotFoundError as e:
    print(f"Error fatal: No se encontró el archivo. {e}")
    exit()

# ESTA ES TU LISTA DE VALIDACIÓN HUMANA (108 papers)
ids_validados = [
    "d1ad08c326d1", "933573e12633", "8581e74341ad", "8d8ab7ed834f", "ff6fb1e2be19",
    "a3d6daa1a396", "b0a263cd3ba1", "eaf6d52d5457", "3f271659124f", "c21a0b99e259",
    "ca6e200d678b", "3f68844ce318", "1f05b7130bac", "733ba5fc919b", "c6e6f6ecfc86",
    "777fe0df0d19", "958e8ae09926", "d84d0ce7a4c8", "84915f5956b8", "a31195146871",
    "0866b31f11c4", "66c76ad14a95", "afea8402003b", "bdf5eac988ad", "2847f25a6987",
    "e33a9f68417e", "5b69b4b177c8", "7d15d84ce20e", "3159c4d063f0", "fc1441e078b0",
    "9cdd576a9db7", "358f64b8021b", "da697160487b", "cab713fe6b41", "de492b348258",
    "c95e30752adf", "7c0bf746ba69", "1b1615a2a91f", "410aff4dd954", "b9e1bf330baf",
    "a59af72ab39c", "5b0090a41d47", "6039788ff154", "9153f4dcf3d6", "4b96859cedec",
    "3c0c667b5363", "cf94a74b8764", "2ea3de6be731", "6c517c5bda80", "56c7d6d62d7c",
    "0672168600bf", "260cc6707374", "a2d7c6427ea6", "7e7db277fd49", "ea1c763936e6",
    "edcffe92f4f7", "d1fc7e47a220", "b9283c8bb52e", "08f457a29ab7", "bd9f05de8774",
    "455162266eca", "e8ac38dcd4f6", "e727426383d4", "fd7c9736c65e", "3d6573117d0b",
    "eac718b2695f", "4c59c898e3d7", "b98dbc59db77", "0b7a68d1a06a", "762d789f17fe",
    "73261bea95b6", "bb87293d7644", "cb831c750a69", "8a3d4a75e493", "ee5e8ed6aa50",
    "6adf36ff1a69", "a0bf6d5dbb2a", "b04f1061de65", "b2f5c867cc6d", "42c958306230",
    "0f11125f1b80", "1710172c2f61", "21ecc353ac74", "eb62900f32b4", "9c540c6b7af5",
    "3e5fff353a4c", "f21bc832abc6", "9e1320ce502d", "dbd6c72cd37b", "b68bd4348e6d",
    "362e76793312", "888d4516378f", "bbf5ed8cca66", "697b132b1c14", "fd5e38820a05",
    "3bbd6f08b6ac", "da95dfe229ec", "61c5ef71efb6", "9275249d37b1", "0473ab551ece",
    "efb1b08a09c7", "6fa69e1a923c", "2cca03b7a82b", "600784de6428", "e94f3a3a8624",
    "81a2071c7d3b", "7f70ba66f24a", "b1fb9424d9f7"
]

# FILTRO: Solo nos quedamos con los que están en la lista
df_sample = df_corpus[df_corpus['doc_id'].isin(ids_validados)].copy()
print(f"✅ Filtro aplicado: Se van a analizar exactamente {len(df_sample)} papers validados.")

# Inyectamos tu inteligencia institucional (CSV de reglas) en el prompt
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
# --- CAMBIO AL NUEVO MODELO DE PRUEBA ---
MODEL_NAME = "llama3.1:8b" 

def classify_abstract_strict(abstract_text):
    prompt = f"""You are a strict and precise scientific evaluator analyzing research abstracts from the Universitat Politècnica de València (UPV) against the Planetary Boundaries (PBs) framework.

Your task is to find the PB with the HIGHEST conceptual similarity to the abstract. You must strictly apply the activation rules and evaluate the exclusion rules. Do not force a match if the scientific connection is weak.

### PLANETARY BOUNDARIES RULES:
{pb_rules}

### ABSTRACT TO EVALUATE:
<text>
{abstract_text}
</text>

### INSTRUCTIONS:
Step 1: Concept Extraction. Identify the core scientific concepts, phenomena, or metrics in the abstract.
Step 2: Similarity Matching. Compare these concepts against the Core Definition and Activation Logic of each PB. Select the PB(s) with the strongest scientific overlap.
Step 3: Exclusion Check. Apply the EXCLUSION RULE. If the rule is explicitly violated, the PB MUST be discarded.
Step 4: Output the final decision in JSON format EXACTLY as follows. You must include a "confidence" score (High, Medium, or Low) evaluating how strong the match is. Return ONLY valid JSON, without any markdown formatting or extra text.

{{
    "reasoning_process": "Analyze the similarity and evaluate the exclusion rules to justify your decision.",
    "assigned_pbs": [
        {{
            "pb_code": "PB1",
            "reason": "Justify why this is the highest similarity match.",
            "confidence": "High"
        }}
    ]
}}
If no PB meets the criteria after applying the strict rules, return {{"reasoning_process": "Explain why similarities were too weak or excluded...", "assigned_pbs": []}}.
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json", # Llama 3.1 respeta muy bien este formato
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.9
        }
    }

    start_time = time.time()
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        result_json = response.json()
        
        llm_response_text = result_json.get("response", "{}")
        eval_time = time.time() - start_time
        return llm_response_text, eval_time
    except Exception as e:
        return json.dumps({"error": str(e)}), time.time() - start_time

# ==========================================
# EXTRAE EL JSON DE FORMA SEGURA
# ==========================================
def parse_llm_output(raw_text):
    try:
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = raw_text[start_idx:end_idx+1]
            data = json.loads(json_str)
        else:
            raise ValueError("No se encontró estructura JSON en la respuesta.")
        
        reasoning = data.get("reasoning_process", "")
        assigned_pbs = data.get("assigned_pbs", [])
        
        if not assigned_pbs or len(assigned_pbs) == 0:
            return reasoning, "None", "N/A"
        else:
            pb_codes_str = ", ".join([item.get("pb_code", "") for item in assigned_pbs])
            confidence_str = ", ".join([item.get("confidence", "Unknown") for item in assigned_pbs])
            return reasoning, pb_codes_str, confidence_str
    except Exception as e:
        return f"Error procesando JSON: {e}", "Error_Formato", "Error"

# ==========================================
# 3 Y 4. BUCLE DE EVALUACIÓN CON GUARDADO SEGURO
# ==========================================
total_papers = len(df_sample)
# --- CAMBIO DE NOMBRE DEL ARCHIVO DE SALIDA ---
output_filename = OUTPUTS_DIR / 'eval_llama3_1_8b_validacion_108.csv'

# Limpiamos el archivo si ya existía para empezar de cero
if os.path.exists(output_filename):
    os.remove(output_filename)

print(f"\nIniciando evaluación ESTRICTA con el modelo: {MODEL_NAME}")
print(f"Los resultados se irán guardando automáticamente en: {output_filename}")
print("-" * 70)

for i, (index, row) in enumerate(df_sample.iterrows(), start=1):
    print(f"Procesando Abstract {i}/{total_papers} (Doc ID: {row['doc_id']})...", end=" ", flush=True)
    
    # 1. Inferencia
    llm_out, t_elapsed = classify_abstract_strict(row['clean_abstract'])
    reasoning, codes, confidence = parse_llm_output(llm_out)
    
    print(f"[{t_elapsed:.2f}s] -> PBs: {codes} | Confianza: {confidence}")
    
    # 2. Guardado en tiempo real
    df_fila = pd.DataFrame([{
        'doc_id': row['doc_id'],
        'llm_predicted_pbs': codes,
        'llm_confidence': confidence,
        'llm_reasoning': reasoning,
        'clean_abstract': row['clean_abstract'],
        'inference_time_sec': t_elapsed
    }])
    
    # Escribir cabeceras solo la primera vez
    if not os.path.isfile(output_filename):
        df_fila.to_csv(output_filename, index=False)
    else:
        df_fila.to_csv(output_filename, mode='a', header=False, index=False)

print("\n" + "=" * 70)
print(f"✅ Completado y asegurado. Resultados en: {output_filename}")