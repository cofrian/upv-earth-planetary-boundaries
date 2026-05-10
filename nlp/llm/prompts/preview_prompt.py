import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_CORPUS_PATH = ROOT_DIR / 'data' / 'corpus' / 'master_corpus_mixto_1000_clean_enriched.csv'
PB_REFERENCE_PATH = ROOT_DIR / 'corpus_PB' / 'data' / 'pb_reference.csv'

# 1. Cargar los datos (Asegúrate de que las rutas son las correctas en tu máquina virtual)
try:
    df_corpus = pd.read_csv(DATA_CORPUS_PATH)
    df_pbs = pd.read_csv(PB_REFERENCE_PATH)
except FileNotFoundError as e:
    print(f"Error al cargar archivos: {e}")
    exit()

# 2. Extraer un abstract de prueba (cogemos el primero, índice 0)
abstract_de_prueba = df_corpus['clean_abstract'].iloc[0]

# 3. Construir las reglas dinámicas desde el CSV de los PBs
pb_rules = ""
for index, row in df_pbs.iterrows():
    pb_rules += f"- PB Code: {row['pb_code']} ({row['pb_name']})\n"
    pb_rules += f"  * Core Definition: {row['short_definition']}\n"
    pb_rules += f"  * UPV Context: Look for terms like: {row['applied_keywords_upv']}\n"
    pb_rules += f"  * ACTIVATION LOGIC: {row['activation_logic']}\n"
    pb_rules += f"  * EXCLUSION RULE (CRITICAL): {row['exclusion_notes']}\n\n"

# 4. Construir el NUEVO Prompt Final (Estricto + Nivel de Confianza)
prompt_final = f"""You are a strict and precise scientific evaluator analyzing research abstracts from the Universitat Politècnica de València (UPV) against the Planetary Boundaries (PBs) framework.

Your task is to find the PB with the HIGHEST conceptual similarity to the abstract. You must strictly apply the activation rules and evaluate the exclusion rules. Do not force a match if the scientific connection is weak.

### PLANETARY BOUNDARIES RULES:
{pb_rules}
### ABSTRACT TO EVALUATE:
"{abstract_de_prueba}"

### INSTRUCTIONS:
Step 1: Concept Extraction. Identify the core scientific concepts, phenomena, or metrics in the abstract.
Step 2: Similarity Matching. Compare these concepts against the Core Definition and Activation Logic of each PB. Select the PB(s) with the strongest scientific overlap.
Step 3: Exclusion Check. Apply the EXCLUSION RULE. If the rule is explicitly violated, the PB MUST be discarded.
Step 4: Output the final decision in JSON format EXACTLY as follows. You must include a "confidence" score (High, Medium, or Low) evaluating how strong the match is.

{{
    "reasoning_process": "Analyze the similarity and evaluate the exclusion rules to justify your decision.",
    "assigned_pbs": [
        {{
            "pb_code": "PB1",
            "reason": "Justify why this is the highest similarity match.",
            "confidence": "High / Medium / Low"
        }}
    ]
}}
If no PB meets the criteria after applying the strict rules, return {{"reasoning_process": "Explain why similarities were too weak or excluded...", "assigned_pbs": []}}.
"""

# 5. Imprimir el resultado por pantalla
print("="*80)
print("🔍 ASÍ ES EXACTAMENTE EL NUEVO PROMPT ESTRICTO QUE RECIBE EL MODELO:")
print("="*80)
print(prompt_final)
print("="*80)
print(f"Longitud total del prompt: {len(prompt_final)} caracteres (aprox {len(prompt_final)//4} tokens).")