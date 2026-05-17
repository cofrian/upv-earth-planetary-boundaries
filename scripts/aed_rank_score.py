"""
Puntuacion por posicion en el ranking.

Para cada PB anotado en el Excel, calcula la contribucion:
   peso_gold / posicion_modelo
donde:
   peso_gold = 3 (1stpb), 2 (2ndpb), 1 (3rdpb)
   posicion_modelo = posicion del PB en el ranking de scores (1=mejor, 9=peor)

Score del documento = suma de contribuciones / maximo posible.
Maximo posible = colocar gold_1st en posicion 1, gold_2nd en 2, gold_3rd en 3.

Salidas:
  docs/eda/aed/figures/20_rank_score.png
  docs/eda/aed/tables/rank_score_perdoc.csv
  docs/eda/aed/tables/rank_score_summary.csv
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nlp/bert_finetuning/outputs_full"
GT = ROOT / "nlp/llm/outputs/ground_truth/validacion_real.csv"
AED = ROOT / "docs/eda/aed"
FIG = AED / "figures"
TAB = AED / "tables"

PB_CODES = [f"PB{i}" for i in range(1, 10)]
SCORE_COLS = [f"score_{c}" for c in PB_CODES]

MODELS = [
    ("baseline_lexical", "lexical"),
    ("baseline_semantic_tfidf", "tfidf"),
    ("backbone_bert_base_uncased", "bert-base"),
    ("backbone_roberta_base", "roberta"),
    ("backbone_allenai_scibert_scivocab_uncased", "scibert"),
    ("backbone_allenai_specter", "specter"),
]

# Pesos por nivel del gold
W_1ST = 3.0
W_2ND = 2.0
W_3RD = 1.0

mpl.rcParams.update({
    "figure.dpi":130, "savefig.dpi":300, "savefig.bbox":"tight",
    "font.family":"DejaVu Sans", "font.size":10.5,
    "axes.titlesize":12.5, "axes.titleweight":"bold",
    "axes.spines.top":False, "axes.spines.right":False,
    "legend.frameon":False, "figure.facecolor":"white",
})


def to_pb(v):
    if pd.isna(v): return None
    try:
        n = int(float(v))
        if 1 <= n <= 9: return f"PB{n}"
    except (ValueError, TypeError):
        pass
    return None


# Load gold
gt = pd.read_csv(GT, sep=";")
gt.columns = [c.strip().lstrip("﻿") for c in gt.columns]
gt["gold_1st"] = gt["1stpb"].map(to_pb)
gt["gold_2nd"] = gt["2ndpb"].map(to_pb)
gt["gold_3rd"] = gt["3rdpb"].map(to_pb)
gt = gt[gt["gold_1st"].notna()].drop_duplicates("doc_id", keep="first")
print(f"[load] gold docs: {len(gt)}")
gt_idx = gt.set_index("doc_id")
gold_ids = set(gt["doc_id"].astype(str))

# Load predictions
preds = {}
for folder, short in MODELS:
    df = pd.read_csv(OUT / folder / "predictions_all_docs.csv", low_memory=False)
    df = df[df["doc_id"].astype(str).isin(gold_ids)].drop_duplicates("doc_id", keep="first")
    preds[short] = df.set_index("doc_id")

common = sorted(set.intersection(*[set(d.index) for d in preds.values()]) & gold_ids)
print(f"[load] common ids: {len(common)}")


def rank_of_pb(scores_row, pb_code):
    """Posicion (1..9) de pb_code en el ranking descendente de scores."""
    scores = scores_row[SCORE_COLS].values.astype(float)
    order = np.argsort(-scores)  # indices sorted by descending score
    pb_idx = PB_CODES.index(pb_code)
    return int(np.where(order == pb_idx)[0][0]) + 1  # 1-based


per_doc_rows = []
agg_rows = {s: {"score": 0.0, "max": 0.0,
                "rank_1st_sum": 0, "rank_2nd_sum": 0, "rank_3rd_sum": 0,
                "n_with_2nd": 0, "n_with_3rd": 0,
                "rank_1st_top1": 0, "rank_1st_top2": 0, "rank_1st_top3": 0}
           for _, s in MODELS}

for did in common:
    g1 = gt_idx.loc[did, "gold_1st"]
    g2 = gt_idx.loc[did, "gold_2nd"]
    g3 = gt_idx.loc[did, "gold_3rd"]

    # Max posible: 1st en pos 1, 2nd en pos 2, 3rd en pos 3
    max_pts = W_1ST / 1
    if g2: max_pts += W_2ND / 2
    if g3: max_pts += W_3RD / 3

    row = {"doc_id": did, "gold_1st": g1, "gold_2nd": g2 or "", "gold_3rd": g3 or ""}

    for _, short in MODELS:
        sr = preds[short].loc[did]
        r1 = rank_of_pb(sr, g1)
        contrib = W_1ST / r1
        agg_rows[short]["rank_1st_sum"] += r1
        if r1 == 1: agg_rows[short]["rank_1st_top1"] += 1
        if r1 <= 2: agg_rows[short]["rank_1st_top2"] += 1
        if r1 <= 3: agg_rows[short]["rank_1st_top3"] += 1

        r2_str = ""
        if g2:
            r2 = rank_of_pb(sr, g2)
            contrib += W_2ND / r2
            agg_rows[short]["rank_2nd_sum"] += r2
            agg_rows[short]["n_with_2nd"] += 1
            r2_str = str(r2)

        r3_str = ""
        if g3:
            r3 = rank_of_pb(sr, g3)
            contrib += W_3RD / r3
            agg_rows[short]["rank_3rd_sum"] += r3
            agg_rows[short]["n_with_3rd"] += 1
            r3_str = str(r3)

        norm = contrib / max_pts
        agg_rows[short]["score"] += contrib
        agg_rows[short]["max"] += max_pts

        row[f"{short}_rank_1st"] = r1
        row[f"{short}_rank_2nd"] = r2_str
        row[f"{short}_rank_3rd"] = r3_str
        row[f"{short}_score"] = round(contrib, 3)
        row[f"{short}_score_norm"] = round(norm, 3)

    per_doc_rows.append(row)

per_doc = pd.DataFrame(per_doc_rows)
per_doc.to_csv(TAB / "rank_score_perdoc.csv", index=False)

# Aggregate
summary_rows = []
n = len(common)
for _, short in MODELS:
    a = agg_rows[short]
    avg_rank_1st = a["rank_1st_sum"] / n
    avg_rank_2nd = a["rank_2nd_sum"] / a["n_with_2nd"] if a["n_with_2nd"] else None
    summary_rows.append({
        "model": short,
        "score_norm_global": round(a["score"] / a["max"], 3),
        "rank_1st_avg": round(avg_rank_1st, 2),
        "rank_2nd_avg": round(avg_rank_2nd, 2) if avg_rank_2nd else None,
        "pct_1st_in_top1": round(a["rank_1st_top1"] / n * 100, 1),
        "pct_1st_in_top2": round(a["rank_1st_top2"] / n * 100, 1),
        "pct_1st_in_top3": round(a["rank_1st_top3"] / n * 100, 1),
    })
summary = pd.DataFrame(summary_rows).sort_values("score_norm_global", ascending=False).reset_index(drop=True)
summary.to_csv(TAB / "rank_score_summary.csv", index=False)

print("\n=== PUNTUACION POR POSICION EN EL RANKING ===")
print(f"Pesos: 1stpb={W_1ST}, 2ndpb={W_2ND}, 3rdpb={W_3RD}")
print(f"Contribucion = peso_gold / posicion_modelo")
print(f"n = {n} docs anotados\n")
print(summary.to_string(index=False))

# ---------------------------------------------------------------------------
# Figure 20 - rank score
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw=dict(wspace=0.3))

ax = axes[0]
order = summary["model"].tolist()
xs = np.arange(len(order))
colors = ["#1F4E79" if i == 0 else "#7E9DB3" for i in range(len(order))]
b = ax.bar(xs, summary["score_norm_global"].values, color=colors, edgecolor="white")
for bar, v in zip(b, summary["score_norm_global"]):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.01, f"{v:.2f}",
            ha="center", fontsize=11, weight="bold", color="#1F4E79")
ax.set_xticks(xs); ax.set_xticklabels(order, rotation=20, ha="right")
ax.set_ylim(0, 1.0); ax.set_ylabel("score normalizado (0 - 1)")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("a. Score por posicion en el ranking (ponderado)",
             loc="left", weight="bold")

# Distribucion de posicion del 1stpb
ax = axes[1]
w = 0.27
b1 = ax.bar(xs - w, summary["pct_1st_in_top1"].values, w,
            color="#1F4E79", label="1stpb en pos 1")
b2 = ax.bar(xs, summary["pct_1st_in_top2"].values, w,
            color="#3F7CAC", label="1stpb en top 2")
b3 = ax.bar(xs + w, summary["pct_1st_in_top3"].values, w,
            color="#9ECAE1", label="1stpb en top 3")
for bars, key in [(b1, "pct_1st_in_top1"), (b2, "pct_1st_in_top2"), (b3, "pct_1st_in_top3")]:
    for bar, v in zip(bars, summary[key]):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.5, f"{v:.0f}",
                ha="center", fontsize=8, color="#333")
ax.set_xticks(xs); ax.set_xticklabels(order, rotation=20, ha="right")
ax.set_ylim(0, 105); ax.set_ylabel("%")
ax.legend(loc="upper right", fontsize=9)
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("b. Donde cae el PB principal del Excel en el ranking del modelo",
             loc="left", weight="bold")

fig.suptitle(f"Figure 20 - Puntuacion por posicion: peso_gold / posicion_modelo (n={n})",
             fontsize=13, weight="bold", x=0.04, ha="left", y=1.02)
fig.text(0.04, 0.97,
         f"Pesos: 1stpb x{W_1ST:.0f}, 2ndpb x{W_2ND:.0f}, 3rdpb x{W_3RD:.0f}. "
         f"Top-1 da credito completo, top-2 la mitad, top-3 un tercio, etc.",
         fontsize=9.5, color="#666", style="italic")
fig.savefig(FIG / "20_rank_score.png", dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(FIG / "20_rank_score.pdf", dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\n  -> {(FIG/'20_rank_score.png').relative_to(ROOT)}")
