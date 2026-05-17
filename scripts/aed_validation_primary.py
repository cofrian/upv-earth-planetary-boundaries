"""
Validacion contra el Excel anotado a mano (validacion_real.csv).

Metricas:
  1. Top-1 acierta el PB principal: pred_top1 == gold_1st
  2. PB principal entre top-1 o top-2: gold_1st in {pred_top1, pred_top2}
  3. Multilabel: precision / recall sobre el conjunto gold = {1stpb, 2ndpb, 3rdpb}
  4. Cobertura: % de PBs predichos que estan en el gold (de todos los que ha sacado, cuantos ha acertado)

Outputs:
  docs/eda/aed/figures/17_primary_pb_accuracy.png     barras top-1 / top-2 / multilabel hit
  docs/eda/aed/figures/18_multilabel_pr.png           precision-recall por modelo
  docs/eda/aed/tables/validation_primary.csv          por doc | gold_1st | gold_set | <modelo>_top1 | etc.
  docs/eda/aed/tables/validation_primary_summary.csv  resumen por modelo
"""
from __future__ import annotations

import re
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nlp/bert_finetuning/outputs_full"
GT = ROOT / "nlp/llm/outputs/ground_truth/validacion_real.csv"
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
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
    "lexical":"#9e9e9e", "tfidf":"#bdbdbd", "bert-base":"#7986cb",
    "roberta":"#ff8a65", "scibert":"#26a69a", "specter":"#1F4E79",
}

mpl.rcParams.update({
    "figure.dpi":130, "savefig.dpi":300, "savefig.bbox":"tight",
    "font.family":"DejaVu Sans", "font.size":10.5,
    "axes.titlesize":12.5, "axes.titleweight":"bold",
    "axes.spines.top":False, "axes.spines.right":False,
    "legend.frameon":False, "figure.facecolor":"white",
})

SAVE_KW = dict(dpi=300, bbox_inches="tight", facecolor="white")


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", **SAVE_KW)
    fig.savefig(FIG / f"{name}.pdf", **SAVE_KW)
    plt.close(fig)
    print(f"  -> {(FIG/f'{name}.png').relative_to(ROOT)}")


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


# ---------------------------------------------------------------------------
# Load gold from Excel
# ---------------------------------------------------------------------------
print("[load] gold annotations")
gt = pd.read_csv(GT, sep=";")
gt.columns = [c.strip().lstrip("﻿") for c in gt.columns]
gt["gold_1st"] = gt["1stpb"].map(to_pb)
gt["gold_2nd"] = gt["2ndpb"].map(to_pb)
gt["gold_3rd"] = gt["3rdpb"].map(to_pb)

def _gold_set(row):
    s = set()
    for c in ("gold_1st", "gold_2nd", "gold_3rd"):
        if row[c]: s.add(row[c])
    return s

gt["gold_set"] = gt.apply(_gold_set, axis=1)
gt_valid = gt[gt["gold_1st"].notna()].copy()
print(f"  total rows: {len(gt)} | with 1stpb: {len(gt_valid)}")
print(f"  with 2ndpb: {gt_valid['gold_2nd'].notna().sum()}")
print(f"  with 3rdpb: {gt_valid['gold_3rd'].notna().sum()}")
print(f"  avg PBs/gold: {gt_valid['gold_set'].map(len).mean():.2f}")

gt_valid = gt_valid.drop_duplicates(subset=["doc_id"], keep="first")
print(f"  unique doc_ids: {len(gt_valid)}")

# ---------------------------------------------------------------------------
# Load model predictions (only docs that are in gt_valid)
# ---------------------------------------------------------------------------
print("\n[load] model predictions")
gold_ids = set(gt_valid["doc_id"].astype(str))
preds = {}
for folder, short in MODELS:
    p = OUT / folder / "predictions_all_docs.csv"
    df = pd.read_csv(p, low_memory=False)
    df = df[df["doc_id"].astype(str).isin(gold_ids)].copy()
    df = df.drop_duplicates(subset=["doc_id"], keep="first")
    df["top1_set"] = df["pred_top1"].map(lambda x: {x} if pd.notna(x) and x in PB_CODES else set())
    df["top2_set"] = df.apply(
        lambda r: ({r["pred_top1"]} if r["pred_top1"] in PB_CODES else set()) |
                  ({r["pred_top2"]} if r["pred_top2"] in PB_CODES else set()),
        axis=1
    )
    df["multi_set"] = df["pred_multilabel"].map(parse_label_set)
    preds[short] = df.set_index("doc_id")
    print(f"  {short}: {len(df)} docs (intersected with gold)")

# Common ids across all models
common = set(gt_valid["doc_id"].astype(str))
for short, df in preds.items():
    common &= set(df.index.astype(str))
common = sorted(common)
print(f"  common ids = {len(common)}")

gt_idx = gt_valid.set_index("doc_id")

# ---------------------------------------------------------------------------
# Per-doc table + per-model metrics
# ---------------------------------------------------------------------------
print("\n[build] per-doc validation")
rows = []
per_model_stats = {s: {"primary_top1": 0, "primary_top2": 0,
                       "total_pred_pbs": 0, "correct_pred_pbs": 0,
                       "total_gold_pbs": 0, "covered_gold_pbs": 0,
                       "exact_match": 0, "any_overlap": 0}
                   for _, s in MODELS}

for did in common:
    gold_1st = gt_idx.loc[did, "gold_1st"]
    gold_set = gt_idx.loc[did, "gold_set"]
    row = {"doc_id": did, "gold_1st": gold_1st,
           "gold_set": ",".join(sorted(gold_set)), "n_gold": len(gold_set)}
    for _, short in MODELS:
        pr = preds[short].loc[did]
        top1 = pr["pred_top1"] if pr["pred_top1"] in PB_CODES else None
        top2 = pr["pred_top2"] if pr["pred_top2"] in PB_CODES else None
        multi = pr["multi_set"] if isinstance(pr["multi_set"], set) else set()

        is_top1 = (top1 == gold_1st)
        is_top2 = (gold_1st in {top1, top2})
        n_pred = len(multi)
        n_correct = len(multi & gold_set)
        is_exact = (multi == gold_set)
        any_overlap = bool(multi & gold_set)

        row[f"{short}_top1"] = top1 or ""
        row[f"{short}_top2"] = top2 or ""
        row[f"{short}_multi"] = ",".join(sorted(multi))
        row[f"{short}_hits_primary_t1"] = int(is_top1)
        row[f"{short}_hits_primary_t2"] = int(is_top2)
        row[f"{short}_n_pred"] = n_pred
        row[f"{short}_n_correct_in_pred"] = n_correct

        s = per_model_stats[short]
        s["primary_top1"] += int(is_top1)
        s["primary_top2"] += int(is_top2)
        s["total_pred_pbs"] += n_pred
        s["correct_pred_pbs"] += n_correct
        s["total_gold_pbs"] += len(gold_set)
        s["covered_gold_pbs"] += n_correct
        s["exact_match"] += int(is_exact)
        s["any_overlap"] += int(any_overlap)
    rows.append(row)

per_doc = pd.DataFrame(rows)
per_doc.to_csv(TAB / "validation_primary.csv", index=False)
print(f"  -> {(TAB/'validation_primary.csv').relative_to(ROOT)}")

# Summary table
n = len(common)
summary_rows = []
for _, short in MODELS:
    s = per_model_stats[short]
    prec = s["correct_pred_pbs"] / s["total_pred_pbs"] if s["total_pred_pbs"] else 0
    rec = s["covered_gold_pbs"] / s["total_gold_pbs"] if s["total_gold_pbs"] else 0
    f1 = 2*prec*rec / (prec+rec) if (prec+rec) else 0
    summary_rows.append({
        "model": short,
        "n_docs": n,
        "primary_top1_acc": round(s["primary_top1"]/n, 3),       # PB principal acertado como top-1
        "primary_top2_acc": round(s["primary_top2"]/n, 3),       # PB principal en top-1 o top-2
        "multi_exact_match": round(s["exact_match"]/n, 3),       # conjunto idéntico
        "multi_any_overlap": round(s["any_overlap"]/n, 3),       # al menos una PB en comun
        "multi_precision": round(prec, 3),  # de PBs predichos, cuantos son del gold
        "multi_recall": round(rec, 3),      # de PBs del gold, cuantos predichos
        "multi_f1": round(f1, 3),
        "total_pred_pbs": s["total_pred_pbs"],
        "correct_pred_pbs": s["correct_pred_pbs"],
        "total_gold_pbs": s["total_gold_pbs"],
    })
summary = pd.DataFrame(summary_rows)
summary.to_csv(TAB / "validation_primary_summary.csv", index=False)
print("\n[summary]")
print(summary.to_string(index=False))

# ---------------------------------------------------------------------------
# Figure 17 - PB principal: top-1 vs top-2 hit
# ---------------------------------------------------------------------------
print("\n[fig 17] primary PB accuracy (top-1 vs top-2)")
fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw=dict(wspace=0.3))

ax = axes[0]
xs = np.arange(len(summary))
w = 0.36
b1 = ax.bar(xs - w/2, summary["primary_top1_acc"].values, w,
            color="#1F4E79", edgecolor="white", label="acierta como top-1")
b2 = ax.bar(xs + w/2, summary["primary_top2_acc"].values, w,
            color="#6BAED6", edgecolor="white", label="entre top-1 o top-2")
for b, v in list(zip(b1, summary["primary_top1_acc"])) + list(zip(b2, summary["primary_top2_acc"])):
    ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v*100:.0f}%",
            ha="center", fontsize=9, color="#333", weight="bold")
ax.set_xticks(xs); ax.set_xticklabels(summary["model"], rotation=20, ha="right")
ax.set_ylim(0, 1.05); ax.set_ylabel("hit rate")
ax.legend(loc="upper left", fontsize=9.5)
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("a. Acertar el PB principal del Excel", loc="left", weight="bold")

# (b) multilabel exact vs overlap
ax = axes[1]
b1 = ax.bar(xs - w/2, summary["multi_exact_match"].values, w,
            color="#2e8b57", edgecolor="white", label="conjunto exacto")
b2 = ax.bar(xs + w/2, summary["multi_any_overlap"].values, w,
            color="#a8d5b3", edgecolor="white", label="al menos un PB en comun")
for b, v in list(zip(b1, summary["multi_exact_match"])) + list(zip(b2, summary["multi_any_overlap"])):
    ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v*100:.0f}%",
            ha="center", fontsize=9, color="#333", weight="bold")
ax.set_xticks(xs); ax.set_xticklabels(summary["model"], rotation=20, ha="right")
ax.set_ylim(0, 1.05); ax.set_ylabel("hit rate")
ax.legend(loc="upper left", fontsize=9.5)
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("b. Acertar el conjunto completo de PBs del Excel", loc="left", weight="bold")

fig.suptitle(f"Figure 17 - Validacion contra Excel anotado (n={n})",
             fontsize=14, weight="bold", x=0.04, ha="left", y=1.02)
fig.text(0.04, 0.97,
         "Izquierda: PB principal (columna 1stpb). Derecha: conjunto {1stpb, 2ndpb, 3rdpb}.",
         fontsize=10, color="#666", style="italic")
save(fig, "17_primary_pb_accuracy")

# ---------------------------------------------------------------------------
# Figure 18 - Multilabel precision / recall / F1
# ---------------------------------------------------------------------------
print("\n[fig 18] multilabel precision/recall/F1")
fig, ax = plt.subplots(figsize=(11, 5.5))
w = 0.27
xs = np.arange(len(summary))
b1 = ax.bar(xs - w, summary["multi_precision"].values, w,
            color="#1F4E79", edgecolor="white", label="precision\n(de lo predicho, % correcto)")
b2 = ax.bar(xs, summary["multi_recall"].values, w,
            color="#3F7CAC", edgecolor="white", label="recall\n(de lo anotado, % cubierto)")
b3 = ax.bar(xs + w, summary["multi_f1"].values, w,
            color="#9ECAE1", edgecolor="white", label="F1")
for bars, key in [(b1, "multi_precision"), (b2, "multi_recall"), (b3, "multi_f1")]:
    for b, v in zip(bars, summary[key]):
        ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v:.2f}",
                ha="center", fontsize=8.5, color="#333")
ax.set_xticks(xs); ax.set_xticklabels(summary["model"], rotation=20, ha="right")
ax.set_ylim(0, 1.05); ax.set_ylabel("score")
ax.legend(loc="upper left", fontsize=9, bbox_to_anchor=(1.0, 1.0))
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title(f"Figure 18 - Validacion multilabel: precision, recall y F1 sobre todos los PBs anotados (n={n})",
             loc="left", weight="bold")
ax.text(0, 1.02,
        "Precision = aciertos / total predichos por el modelo. "
        "Recall = aciertos / total anotados en el Excel.",
        transform=ax.transAxes, fontsize=9.5, color="#666", style="italic")
save(fig, "18_multilabel_pr")

# Console preview
print("\n[preview] primeros 10 docs:")
print(per_doc.head(10).to_string(index=False))
print("\n[done]")
