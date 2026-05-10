import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / 'outputs'
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# 1. RUTAS DE LOS ARCHIVOS
# ==========================================
ruta_humano = OUTPUTS_DIR / 'validacion_real.csv'
ruta_gemma  = OUTPUTS_DIR / 'eval_gemma4_26b_validacion_108.csv'
ruta_qwen   = OUTPUTS_DIR / 'eval_qwen2.5_14b_validacion_108.csv'

def cargar_csv(ruta):
    try:
        return pd.read_csv(ruta, sep=None, engine='python', encoding='utf-8-sig')
    except UnicodeDecodeError:
        return pd.read_csv(ruta, sep=None, engine='python', encoding='latin1')

print("Preparando el ring para la batalla...")
df_human = cargar_csv(ruta_humano)
df_gemma = cargar_csv(ruta_gemma)
df_qwen  = cargar_csv(ruta_qwen)

# Limpiar columnas
df_human.columns = df_human.columns.str.strip().str.lower()
df_gemma.columns = df_gemma.columns.str.strip().str.lower()
df_qwen.columns  = df_qwen.columns.str.strip().str.lower()

# Limpiar IDs
df_human['doc_id'] = df_human['doc_id'].astype(str).str.strip()
df_gemma['doc_id'] = df_gemma['doc_id'].astype(str).str.strip()
df_qwen['doc_id']  = df_qwen['doc_id'].astype(str).str.strip()

# ==========================================
# NUEVO: Formatear TODAS las etiquetas humanas
# ==========================================
# Definimos las columnas a mirar (excluyendo pb_drive)
cols_pb_human = ['1stpb', '2ndpb', '3rdpb', '4thpb', '5thpb', '6thpb']

def extraer_todos_pbs_humano(row):
    pbs = set() # Usamos set para evitar duplicados
    for col in cols_pb_human:
        if col in row.index:
            val = str(row[col]).strip()
            if val.lower() not in ['nan', 'none', '']:
                if val.endswith('.0'): val = val[:-2]
                if val.isdigit():
                    pbs.add(f"PB{val}")
                elif val.upper().startswith('PB'):
                    pbs.add(val.upper())
    
    if len(pbs) == 0:
        return 'None'
    # Devuelve los PBs ordenados y separados por comas
    return ', '.join(sorted(list(pbs)))

df_human['Humano'] = df_human.apply(extraer_todos_pbs_humano, axis=1)

# ==========================================
# Extraer el primer PB de los modelos
# ==========================================
def extract_pb(val):
    val = str(val).strip()
    if val.lower() in ['nan', 'none', '']: return 'None'
    return val.split(',')[0].strip()

df_gemma['Gemma_PB'] = df_gemma['llm_predicted_pbs'].apply(extract_pb)
df_qwen['Qwen_PB']   = df_qwen['llm_predicted_pbs'].apply(extract_pb)

# Preparar DataFrames con los razonamientos
df_gemma_clean = df_gemma[['doc_id', 'Gemma_PB', 'llm_reasoning', 'clean_abstract']].rename(columns={'llm_reasoning': 'Gemma_Reasoning'})
df_qwen_clean  = df_qwen[['doc_id', 'Qwen_PB', 'llm_reasoning']].rename(columns={'llm_reasoning': 'Qwen_Reasoning'})

# ==========================================
# 2. ENFRENTAMIENTO (JOIN Y FILTRO)
# ==========================================
df_batalla = df_human[['doc_id', 'Humano']].merge(df_qwen_clean, on='doc_id', how='inner')
df_batalla = df_batalla.merge(df_gemma_clean, on='doc_id', how='inner')

# FILTRO MÁGICO: Solo nos quedamos con los papers donde Qwen y Gemma NO están de acuerdo
df_discrepancias = df_batalla[df_batalla['Qwen_PB'] != df_batalla['Gemma_PB']].copy()

print("\n" + "⚔️"*20)
print(f" BATALLA DE TITANES: Qwen 2.5 (14B) vs Gemma 4 (26B)")
print("⚔️"*20)
print(f"Total de papers analizados: {len(df_batalla)}")
print(f"Total de discrepancias (Donde piensan distinto): {len(df_discrepancias)}")

# Reordenar columnas para leerlo bien
df_discrepancias = df_discrepancias[['doc_id', 'Humano', 'Qwen_PB', 'Gemma_PB', 'Qwen_Reasoning', 'Gemma_Reasoning', 'clean_abstract']]

# Guardar el reporte
ruta_batalla = OUTPUTS_DIR / 'Batalla_Qwen_vs_Gemma.csv'
df_discrepancias.to_csv(ruta_batalla, index=False, encoding='utf-8-sig')
print(f"\n✅ Reporte de batalla guardado en: {ruta_batalla}")
print("Ábrelo en Excel/CSV, lee los razonamientos y decide quién tiene la razón.")