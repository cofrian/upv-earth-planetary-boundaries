"""
Asignacion final: top-3 PBs por paper con el mejor metodo (TF-IDF).

Justificacion del metodo:
- TF-IDF gana en todas las metricas medidas:
  - 63% acierto top-1 del PB principal humano
  - 77% en top-2, 83% en top-3
  - F1 multilabel = 0.61
  - Score por posicion = 0.77
  - Recupera 80% de PBs anotados en el top-3 (104 de 130)

Output: data/corpus/pb_assignments_top3.csv
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
PREDS = ROOT / "nlp/bert_finetuning/outputs_full/baseline_semantic_tfidf/predictions_all_docs.csv"
OUT_CSV = ROOT / "data/corpus/pb_assignments_top3.csv"

PB_CODES = [f"PB{i}" for i in range(1, 10)]
SCORE_COLS = [f"score_{c}" for c in PB_CODES]
PB_NAMES = {
    "PB1": "Climate Change",
    "PB2": "Ocean Acidification",
    "PB3": "Stratospheric Ozone Depletion",
    "PB4": "Biogeochemical Flows",
    "PB5": "Freshwater Use",
    "PB6": "Land-System Change",
    "PB7": "Biosphere Integrity",
    "PB8": "Novel Entities",
    "PB9": "Atmospheric Aerosol Loading",
}

print("[load] predictions")
pr = pd.read_csv(PREDS, low_memory=False)
print(f"  {len(pr):,} papers etiquetados")

print("[load] corpus metadata")
co = pd.read_csv(CORPUS,
                 usecols=["doc_id", "title", "year", "doi", "journal", "source"],
                 low_memory=False)

print("[merge]")
df = pr.merge(co, on="doc_id", how="left", suffixes=("", "_corpus"))
# title may exist in both; keep predictions title if corpus is NaN
if "title_corpus" in df.columns:
    df["title"] = df["title"].fillna(df["title_corpus"])
    df = df.drop(columns=["title_corpus"])

print("[rank] top-3 PBs by score")
scores = df[SCORE_COLS].values.astype(float)
order = np.argsort(-scores, axis=1)  # desc

rank1_idx = order[:, 0]
rank2_idx = order[:, 1]
rank3_idx = order[:, 2]

def code(i): return PB_CODES[i]
def name(i): return PB_NAMES[PB_CODES[i]]
def score(i, row): return scores[row, i]

df["pb1"] = [code(i) for i in rank1_idx]
df["pb1_name"] = [name(i) for i in rank1_idx]
df["pb1_score"] = [round(float(scores[r, i]), 4) for r, i in enumerate(rank1_idx)]

df["pb2"] = [code(i) for i in rank2_idx]
df["pb2_name"] = [name(i) for i in rank2_idx]
df["pb2_score"] = [round(float(scores[r, i]), 4) for r, i in enumerate(rank2_idx)]

df["pb3"] = [code(i) for i in rank3_idx]
df["pb3_name"] = [name(i) for i in rank3_idx]
df["pb3_score"] = [round(float(scores[r, i]), 4) for r, i in enumerate(rank3_idx)]

# Confidence margins
df["margin_1_2"] = (df["pb1_score"] - df["pb2_score"]).round(4)
df["margin_2_3"] = (df["pb2_score"] - df["pb3_score"]).round(4)

# Confidence label based on margin_1_2
def conf_label(m):
    if m >= 0.05: return "alta"
    if m >= 0.02: return "media"
    return "baja"
df["pb1_confidence"] = df["margin_1_2"].map(conf_label)

# Output schema
out_cols = [
    "doc_id", "title", "year", "doi", "journal", "source",
    "pb1", "pb1_name", "pb1_score",
    "pb2", "pb2_name", "pb2_score",
    "pb3", "pb3_name", "pb3_score",
    "margin_1_2", "margin_2_3", "pb1_confidence",
]
out = df[out_cols].copy()
out.to_csv(OUT_CSV, index=False)
print(f"\n  -> {OUT_CSV.relative_to(ROOT)}  ({len(out):,} filas)")

# Summary
print("\n=== DISTRIBUCION PB1 (PB principal) ===")
print(out["pb1"].value_counts().reindex(PB_CODES).to_string())
print(f"\n=== CONFIANZA PB1 ===")
print(out["pb1_confidence"].value_counts().to_string())

print("\n=== EJEMPLOS ===")
sample = out[["doc_id", "title", "pb1", "pb1_score", "pb2", "pb2_score", "pb3", "pb3_score", "pb1_confidence"]].head(8)
print(sample.to_string(index=False, max_colwidth=50))
