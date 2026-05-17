"""
Formula de exito ponderada para evaluar los 6 modelos.

Idea: no todas las predicciones valen lo mismo. Acertar el PB principal
del Excel pesa mas que acertar uno secundario; un falso positivo penaliza
pero menos que un miss del primario.

Score por documento:

  +3.0  si pred_top1 == gold_1st        (acierto principal estricto)
  +1.5  si gold_1st in {top1, top2}      pero top1 != gold_1st  (ranking parcial)
  +1.0  por cada gold_2nd presente en pred_multilabel
  +0.5  por cada gold_3rd presente en pred_multilabel
  -0.25 por cada PB de pred_multilabel que NO esta en gold_set (falso positivo)

Maximo posible por documento:
   3.0  (top1 estricto)
 + 1.0  si el doc tiene gold_2nd
 + 0.5  si el doc tiene gold_3rd

Score normalizado = score_obtenido / max_posible. Promediamos por modelo.

Sale en docs/eda/aed/{figures/19_success_formula.png, tables/success_formula.csv}.
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

MODELS = [
    ("baseline_lexical", "lexical"),
    ("baseline_semantic_tfidf", "tfidf"),
    ("backbone_bert_base_uncased", "bert-base"),
    ("backbone_roberta_base", "roberta"),
    ("backbone_allenai_scibert_scivocab_uncased", "scibert"),
    ("backbone_allenai_specter", "specter"),
]
MODEL_COLORS = {
    "lexical":"#9e9e9e", "tfidf":"#1F4E79", "bert-base":"#7986cb",
    "roberta":"#ff8a65", "scibert":"#26a69a", "specter":"#3F7CAC",
}

# Pesos de la formula
W_TOP1_HIT     = 3.0    # top1 == gold_1st
W_TOP2_PARTIAL = 1.5    # gold_1st en top1/top2 pero no como top1
W_GOLD_2ND     = 1.0    # gold_2nd en pred_multi
W_GOLD_3RD     = 0.5    # gold_3rd en pred_multi
PENALTY_FP     = 0.25   # PB predicho que no esta en gold

mpl.rcParams.update({
    "figure.dpi":130, "savefig.dpi":300, "savefig.bbox":"tight",
    "font.family":"DejaVu Sans", "font.size":10.5,
    "axes.titlesize":12.5, "axes.titleweight":"bold",
    "axes.spines.top":False, "axes.spines.right":False,
    "legend.frameon":False, "figure.facecolor":"white",
})


def parse_label_set(v):
    if pd.isna(v) or v == "":
        return set()
    return set(re.findall(r"PB\d+", str(v)))


def to_pb(v):
    if pd.isna(v):
        return None
    try:
        n = int(float(v))
        if 1 <= n <= 9:
            return f"PB{n}"
    except (ValueError, TypeError):
        pass
    return None


# Load gold
gt = pd.read_csv(GT, sep=";")
gt.columns = [c.strip().lstrip("﻿") for c in gt.columns]
gt["gold_1st"] = gt["1stpb"].map(to_pb)
gt["gold_2nd"] = gt["2ndpb"].map(to_pb)
gt["gold_3rd"] = gt["3rdpb"].map(to_pb)
gt["gold_set"] = gt.apply(
    lambda r: {x for x in (r["gold_1st"], r["gold_2nd"], r["gold_3rd"]) if x}, axis=1
)
gt = gt[gt["gold_1st"].notna()].drop_duplicates(subset=["doc_id"], keep="first")
print(f"[load] gold docs with 1stpb: {len(gt)}")
gt_idx = gt.set_index("doc_id")
gold_ids = set(gt["doc_id"].astype(str))

# Load model predictions
preds = {}
for folder, short in MODELS:
    df = pd.read_csv(OUT / folder / "predictions_all_docs.csv", low_memory=False)
    df = df[df["doc_id"].astype(str).isin(gold_ids)].drop_duplicates("doc_id", keep="first")
    df["multi_set"] = df["pred_multilabel"].map(parse_label_set)
    preds[short] = df.set_index("doc_id")

common = sorted(set.intersection(*[set(d.index) for d in preds.values()]) & gold_ids)
print(f"[load] common ids: {len(common)}")


# Compute formula
rows = []
detail_rows = []
for did in common:
    g1 = gt_idx.loc[did, "gold_1st"]
    g2 = gt_idx.loc[did, "gold_2nd"]
    g3 = gt_idx.loc[did, "gold_3rd"]
    gold_set = gt_idx.loc[did, "gold_set"]

    max_pts = W_TOP1_HIT + (W_GOLD_2ND if g2 else 0) + (W_GOLD_3RD if g3 else 0)

    for _, short in MODELS:
        pr = preds[short].loc[did]
        top1 = pr["pred_top1"] if pr["pred_top1"] in PB_CODES else None
        top2 = pr["pred_top2"] if pr["pred_top2"] in PB_CODES else None
        multi = pr["multi_set"] if isinstance(pr["multi_set"], set) else set()

        pts_principal = 0.0
        if top1 == g1:
            pts_principal = W_TOP1_HIT
        elif g1 in {top1, top2}:
            pts_principal = W_TOP2_PARTIAL

        pts_2nd = W_GOLD_2ND if (g2 and g2 in multi) else 0.0
        pts_3rd = W_GOLD_3RD if (g3 and g3 in multi) else 0.0

        n_fp = len(multi - gold_set)
        pts_penalty = -PENALTY_FP * n_fp

        score = pts_principal + pts_2nd + pts_3rd + pts_penalty
        norm = score / max_pts if max_pts > 0 else 0.0

        rows.append({
            "model": short, "doc_id": did,
            "pts_principal": pts_principal,
            "pts_2nd": pts_2nd, "pts_3rd": pts_3rd,
            "pts_penalty": pts_penalty,
            "score_raw": score, "score_max": max_pts,
            "score_norm": norm,
        })

detail = pd.DataFrame(rows)
detail.to_csv(TAB / "success_formula_perdoc.csv", index=False)

# Aggregate
agg = detail.groupby("model").agg(
    n_docs=("doc_id", "nunique"),
    score_raw_mean=("score_raw", "mean"),
    score_norm_mean=("score_norm", "mean"),
    pts_principal_mean=("pts_principal", "mean"),
    pts_2nd_mean=("pts_2nd", "mean"),
    pts_3rd_mean=("pts_3rd", "mean"),
    pts_penalty_mean=("pts_penalty", "mean"),
    fully_correct=("score_norm", lambda s: float((s == 1.0).mean())),
).reset_index()

# % de top1 cubierto, etc.
extras = []
for _, short in MODELS:
    sub = detail[detail["model"] == short]
    extras.append({
        "model": short,
        "pct_top1_full_credit": (sub["pts_principal"] == W_TOP1_HIT).mean(),
        "pct_top2_partial_credit": (sub["pts_principal"] == W_TOP2_PARTIAL).mean(),
        "pct_principal_missed": (sub["pts_principal"] == 0).mean(),
    })
extras = pd.DataFrame(extras)
agg = agg.merge(extras, on="model")

# Sort by score_norm_mean
agg = agg.sort_values("score_norm_mean", ascending=False).reset_index(drop=True)
agg.to_csv(TAB / "success_formula_summary.csv", index=False)

print("\n=== FORMULA DE EXITO ===")
print(f"Pesos: top1_hit=+{W_TOP1_HIT}  top2_parcial=+{W_TOP2_PARTIAL}  "
      f"gold_2nd=+{W_GOLD_2ND}  gold_3rd=+{W_GOLD_3RD}  FP=-{PENALTY_FP}")
print()
print(agg.to_string(index=False))

# ---------------------------------------------------------------------------
# Figure 19 - success formula breakdown
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1.2, 1], wspace=0.3))

# (a) Stacked breakdown of points
ax = axes[0]
order = agg["model"].tolist()
xs = np.arange(len(order))

pts_p = agg["pts_principal_mean"].values
pts_2 = agg["pts_2nd_mean"].values
pts_3 = agg["pts_3rd_mean"].values
pts_pn = agg["pts_penalty_mean"].values  # ya es negativo

b1 = ax.bar(xs, pts_p, color="#1F4E79", edgecolor="white", label="PB principal (1st)")
b2 = ax.bar(xs, pts_2, bottom=pts_p, color="#3F7CAC", edgecolor="white",
            label="PB secundario (2nd)")
b3 = ax.bar(xs, pts_3, bottom=pts_p+pts_2, color="#9ECAE1", edgecolor="white",
            label="PB terciario (3rd)")
b4 = ax.bar(xs, pts_pn, color="#d63a3a", edgecolor="white", label="penalty FP")

# total label
totals = pts_p + pts_2 + pts_3 + pts_pn
for x, t in zip(xs, totals):
    ax.text(x, max(t+0.07, 0.1), f"{t:.2f}", ha="center",
            fontsize=10, weight="bold", color="#1F4E79")

ax.axhline(0, color="#666", lw=0.6)
ax.set_xticks(xs); ax.set_xticklabels(order, rotation=20, ha="right")
ax.set_ylabel("puntos medios por documento (max ~3.4)")
ax.legend(loc="upper right", fontsize=9)
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("a. Desglose de la formula de exito (puntos medios/doc)",
             loc="left", weight="bold")

# (b) Normalized score and fully-correct rate
ax = axes[1]
b1 = ax.bar(xs - 0.20, agg["score_norm_mean"].values, 0.4,
            color="#1F4E79", edgecolor="white", label="score norm. medio")
b2 = ax.bar(xs + 0.20, agg["fully_correct"].values, 0.4,
            color="#2e8b57", edgecolor="white", label="% docs perfectos (norm=1)")
for b, v in zip(b1, agg["score_norm_mean"]):
    ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v:.2f}",
            ha="center", fontsize=9, color="#1F4E79", weight="bold")
for b, v in zip(b2, agg["fully_correct"]):
    ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v*100:.0f}%",
            ha="center", fontsize=9, color="#2e8b57", weight="bold")
ax.set_xticks(xs); ax.set_xticklabels(order, rotation=20, ha="right")
ax.set_ylabel("ratio")
ax.set_ylim(0, max(agg["score_norm_mean"].max(), 1)*1.1)
ax.legend(loc="upper right", fontsize=9)
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("b. Score normalizado y % de docs perfectos",
             loc="left", weight="bold")

fig.suptitle(f"Figure 19 - Formula de exito ponderada (n={len(common)})",
             fontsize=14, weight="bold", x=0.04, ha="left", y=1.02)
fig.text(0.04, 0.97,
         f"Pesos: top1 +{W_TOP1_HIT}, top2 parcial +{W_TOP2_PARTIAL}, "
         f"gold_2nd +{W_GOLD_2ND}, gold_3rd +{W_GOLD_3RD}, FP -{PENALTY_FP}. "
         f"Score normalizado = obtenido / maximo posible por documento.",
         fontsize=9.5, color="#666", style="italic")
fig.savefig(FIG / "19_success_formula.png", dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(FIG / "19_success_formula.pdf", dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\n  -> {(FIG/'19_success_formula.png').relative_to(ROOT)}")
print(f"  -> {(TAB/'success_formula_summary.csv').relative_to(ROOT)}")
