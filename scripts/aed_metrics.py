"""
Analisis de metricas de los 6 modelos PB sobre el corpus completo + validacion humana.

Inputs:
  nlp/bert_finetuning/outputs_full/{model}/predictions_all_docs.csv
  nlp/bert_finetuning/outputs_full/{model}/predictions_validation.csv
  nlp/bert_finetuning/outputs_full/{model}/metrics.json
  nlp/bert_finetuning/outputs_full/backbone_comparison.csv

Outputs en docs/eda/aed/:
  figures/09_metrics_overview.png    -- micro/macro F1, jaccard, cardinalidad
  figures/10_per_pb_f1.png           -- F1 por PB para cada modelo
  figures/11_coverage_full.png       -- cobertura sobre 31k abstracts
  figures/12_score_distribution.png  -- distribucion de scores por PB para SPECTER
  tables/per_pb_metrics.csv
  tables/coverage_full.csv
  tables/model_agreement_full.csv
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from sklearn.metrics import precision_recall_fscore_support, f1_score

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "nlp/bert_finetuning/outputs_full"
AED = ROOT / "docs/eda/aed"
FIG = AED / "figures"
TAB = AED / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

PB_CODES = [f"PB{i}" for i in range(1, 10)]
PB_NAMES = {
    "PB1": "Climate Change", "PB2": "Ocean Acidification",
    "PB3": "Ozone", "PB4": "Biogeochemical", "PB5": "Freshwater",
    "PB6": "Land-System", "PB7": "Biosphere", "PB8": "Novel Entities",
    "PB9": "Aerosol",
}
PB_COLORS = {
    "PB1": "#1F4E79", "PB2": "#3F7CAC", "PB3": "#6BAED6", "PB9": "#9ECAE1",
    "PB5": "#2E7D32", "PB6": "#558B2F", "PB7": "#81C784",
    "PB4": "#D26F3D", "PB8": "#B53A1E",
}
MODEL_ORDER = [
    "baseline_lexical",
    "baseline_semantic_tfidf",
    "backbone_bert_base_uncased",
    "backbone_roberta_base",
    "backbone_allenai_scibert_scivocab_uncased",
    "backbone_allenai_specter",
]
MODEL_SHORT = {
    "baseline_lexical": "lexical",
    "baseline_semantic_tfidf": "tfidf",
    "backbone_bert_base_uncased": "bert-base",
    "backbone_roberta_base": "roberta",
    "backbone_allenai_scibert_scivocab_uncased": "scibert",
    "backbone_allenai_specter": "specter",
}
MODEL_COLORS = {
    "lexical": "#9e9e9e",
    "tfidf": "#bdbdbd",
    "bert-base": "#7986cb",
    "roberta": "#ff8a65",
    "scibert": "#26a69a",
    "specter": "#1F4E79",
}

mpl.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 10.5,
    "axes.titlesize": 12.5, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#444", "xtick.color": "#444", "ytick.color": "#444",
    "legend.frameon": False, "figure.facecolor": "white",
})

SAVE_KW = dict(dpi=300, bbox_inches="tight", facecolor="white")


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", **SAVE_KW)
    fig.savefig(FIG / f"{name}.pdf", **SAVE_KW)
    plt.close(fig)
    print(f"  -> {(FIG/f'{name}.png').relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Load predictions for every model
# ---------------------------------------------------------------------------
def parse_label_set(value):
    if pd.isna(value):
        return set()
    parts = re.findall(r"PB\d+", str(value))
    return set(parts)


print("[load] predictions for", len(MODEL_ORDER), "models")
preds_all = {}
preds_val = {}
metrics_json = {}
for m in MODEL_ORDER:
    base = OUT_DIR / m
    if not base.exists():
        print(f"  [WARN] missing {m}")
        continue
    pa = pd.read_csv(base / "predictions_all_docs.csv", low_memory=False)
    pv = pd.read_csv(base / "predictions_validation.csv", low_memory=False)
    mj = json.loads((base / "metrics.json").read_text())
    preds_all[m] = pa
    preds_val[m] = pv
    metrics_json[m] = mj
    print(f"  {MODEL_SHORT[m]}: {len(pa)} all, {len(pv)} val")

short_names = [MODEL_SHORT[m] for m in preds_all]


# ---------------------------------------------------------------------------
# Figure 9 - overall metrics (micro/macro F1, Jaccard, cardinality error)
# ---------------------------------------------------------------------------
print("\n[fig 09] overall metrics panel")

modes = ["top1", "threshold_delta"]
metric_keys = ["micro_f1", "macro_f1", "jaccard_samples", "abs_cardinality_error"]
rows = []
for m, mj in metrics_json.items():
    short = MODEL_SHORT[m]
    for mode in modes:
        if mode not in mj:
            continue
        block = mj[mode]
        rows.append({
            "model": short, "mode": mode,
            **{k: block.get(k, np.nan) for k in metric_keys},
            "tau": block.get("tau"), "delta": block.get("delta"),
        })
metrics_df = pd.DataFrame(rows)
metrics_df.to_csv(TAB / "model_metrics_summary.csv", index=False)

fig, axes = plt.subplots(2, 2, figsize=(14, 8), gridspec_kw=dict(hspace=0.45, wspace=0.3))
titles = {
    "micro_f1": "Micro-F1 (multilabel)",
    "macro_f1": "Macro-F1 (multilabel, balance entre PBs)",
    "jaccard_samples": "Jaccard samples (solapamiento conjunto)",
    "abs_cardinality_error": "Error absoluto de cardinalidad (predicho - real)",
}
for ax, key in zip(axes.flat, metric_keys):
    sub = metrics_df.pivot(index="model", columns="mode", values=key)
    sub = sub.reindex(short_names)
    width = 0.35
    xs = np.arange(len(sub.index))
    bars1 = ax.bar(xs - width/2, sub["top1"].values, width, label="top1",
                   color="#90a4ae", edgecolor="white")
    bars2 = ax.bar(xs + width/2, sub.get("threshold_delta", pd.Series(np.nan)).values, width,
                   label="tuned tau-delta", color="#1F4E79", edgecolor="white")
    for bars in (bars1, bars2):
        for b in bars:
            h = b.get_height()
            if not np.isnan(h):
                ax.text(b.get_x()+b.get_width()/2, h + 0.005, f"{h:.2f}",
                        ha="center", fontsize=8.5, color="#333")
    ax.set_xticks(xs); ax.set_xticklabels(sub.index, rotation=20, ha="right")
    ax.set_title(titles[key], loc="left")
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
    ax.set_axisbelow(True)
    if key == "abs_cardinality_error":
        ax.set_ylabel("error abs")
    else:
        ax.set_ylabel("score")
    if key == "micro_f1":
        ax.legend(loc="upper left", fontsize=9)

fig.suptitle("Figure 9 - Metricas globales por modelo (validacion humana, n=149)",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
fig.text(0.05, 0.97,
         "top1 = un solo PB por paper (estricto); tuned = umbral tau/delta optimizado para F1.",
         fontsize=10, color="#666", style="italic")
save(fig, "09_metrics_overview")


# ---------------------------------------------------------------------------
# Figure 10 - per-PB precision / recall / F1 on validation
# ---------------------------------------------------------------------------
print("\n[fig 10] per-PB F1")

def to_label_mat(df_label_col, pb_codes):
    rows = []
    for v in df_label_col:
        labels = parse_label_set(v)
        rows.append([1 if pb in labels else 0 for pb in pb_codes])
    return np.array(rows, dtype=int)

per_pb_rows = []
for m, pv in preds_val.items():
    short = MODEL_SHORT[m]
    if "gold_labels" not in pv.columns:
        continue
    y_true = to_label_mat(pv["gold_labels"], PB_CODES)
    # Prefer threshold_delta predictions (more realistic) - in pv that's pred_multilabel
    y_pred = to_label_mat(pv["pred_multilabel"], PB_CODES)
    p, r, f, sup = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=list(range(len(PB_CODES))), zero_division=0
    )
    for i, pb in enumerate(PB_CODES):
        per_pb_rows.append({
            "model": short, "pb": pb,
            "precision": float(p[i]), "recall": float(r[i]),
            "f1": float(f[i]), "support_true": int(sup[i]),
        })
per_pb = pd.DataFrame(per_pb_rows)
per_pb.to_csv(TAB / "per_pb_metrics.csv", index=False)

# Heatmap model x PB con F1
pivot_f1 = per_pb.pivot(index="model", columns="pb", values="f1").reindex(
    index=short_names, columns=PB_CODES
)

fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1.3, 1], wspace=0.3))

ax = axes[0]
sns.heatmap(pivot_f1, annot=True, fmt=".2f", cmap="YlGn", vmin=0, vmax=1,
            linewidths=0.5, linecolor="white", ax=ax,
            cbar_kws=dict(label="F1"))
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels([f"{c}\n{PB_NAMES[c]}" for c in PB_CODES], rotation=0, fontsize=8)
ax.set_title("a. F1 por PB y por modelo", loc="left", weight="bold")

# support per PB (true)
ax = axes[1]
sup_series = per_pb.groupby("pb")["support_true"].max().reindex(PB_CODES)
ax.barh(sup_series.index, sup_series.values,
        color=[PB_COLORS[c] for c in sup_series.index], edgecolor="white")
for i, (c, v) in enumerate(sup_series.items()):
    ax.text(v+0.5, i, str(int(v)), va="center", fontsize=9, color="#333")
ax.set_xlabel("# papers en validacion con esa PB")
ax.set_title("b. Soporte por PB en el ground truth (n=149)",
             loc="left", weight="bold")

fig.suptitle("Figure 10 - Comportamiento por Planetary Boundary",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
fig.text(0.05, 0.97,
         "F1 leido sobre las 149 etiquetas humanas; ojo a PBs con soporte bajo.",
         fontsize=10, color="#666", style="italic")
save(fig, "10_per_pb_f1")


# ---------------------------------------------------------------------------
# Figure 11 - coverage on the full 31k corpus
# ---------------------------------------------------------------------------
print("\n[fig 11] coverage on full corpus")

cov_rows = []
for m, pa in preds_all.items():
    short = MODEL_SHORT[m]
    total = len(pa)
    counts_top1 = pa["pred_top1"].value_counts().reindex(PB_CODES, fill_value=0)
    pct_top1 = (counts_top1 / total * 100).round(2)
    # multilabel coverage: how often each PB appears in pred_multilabel
    multi = pa["pred_multilabel"].fillna("").map(parse_label_set)
    counts_multi = pd.Series([pb for s in multi for pb in s]).value_counts().reindex(PB_CODES, fill_value=0)
    pct_multi = (counts_multi / total * 100).round(2)
    for pb in PB_CODES:
        cov_rows.append({
            "model": short, "pb": pb,
            "n_top1": int(counts_top1[pb]), "pct_top1": float(pct_top1[pb]),
            "n_multi": int(counts_multi[pb]), "pct_multi": float(pct_multi[pb]),
        })
cov = pd.DataFrame(cov_rows)
cov.to_csv(TAB / "coverage_full.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), gridspec_kw=dict(wspace=0.3))

# (a) Stacked bars: top1 share per model
ax = axes[0]
piv = cov.pivot(index="model", columns="pb", values="pct_top1").reindex(
    index=short_names, columns=PB_CODES
)
bottom = np.zeros(len(piv))
for c in PB_CODES:
    ax.barh(piv.index, piv[c].values, left=bottom,
            color=PB_COLORS[c], edgecolor="white", linewidth=0.5, label=c)
    bottom += piv[c].values
ax.set_xlim(0, 100); ax.set_xlabel("% del corpus")
ax.legend(ncol=9, loc="upper center", bbox_to_anchor=(0.5, -0.13),
          fontsize=8.5, handletextpad=0.4, columnspacing=0.8)
ax.set_title("a. Cobertura top-1 sobre los 31k abstracts", loc="left", weight="bold")

# (b) Heatmap multi-label coverage
ax = axes[1]
piv_m = cov.pivot(index="model", columns="pb", values="pct_multi").reindex(
    index=short_names, columns=PB_CODES
)
sns.heatmap(piv_m, annot=True, fmt=".1f", cmap="Blues",
            linewidths=0.5, linecolor="white", ax=ax,
            cbar_kws=dict(label="% del corpus (multilabel)"))
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels([f"{c}\n{PB_NAMES[c]}" for c in PB_CODES], rotation=0, fontsize=8)
ax.set_title("b. Cobertura multilabel (% de papers que reciben cada PB)",
             loc="left", weight="bold")

fig.suptitle(f"Figure 11 - Reparto de etiquetas PB sobre el corpus completo (N={len(preds_all[list(preds_all)[0]]):,})",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
save(fig, "11_coverage_full")


# ---------------------------------------------------------------------------
# Figure 12 - score distribution per PB for SPECTER
# ---------------------------------------------------------------------------
print("\n[fig 12] score distribution (specter)")

sp = preds_all.get("backbone_allenai_specter")
if sp is not None:
    score_cols = [f"score_{c}" for c in PB_CODES if f"score_{c}" in sp.columns]
    fig, ax = plt.subplots(figsize=(13, 5.5))
    data = [sp[c].dropna().values for c in score_cols]
    parts = ax.violinplot(data, showmeans=False, showmedians=True, widths=0.85)
    for i, body in enumerate(parts["bodies"]):
        body.set_facecolor(PB_COLORS[PB_CODES[i]])
        body.set_edgecolor("white"); body.set_alpha(0.85)
    for key in ("cmedians", "cbars", "cmins", "cmaxes"):
        if key in parts:
            parts[key].set_color("#444"); parts[key].set_lw(1)
    ax.set_xticks(range(1, len(PB_CODES)+1))
    ax.set_xticklabels([f"{c}\n{PB_NAMES[c]}" for c in PB_CODES], fontsize=8.5)
    ax.set_ylabel("score (cosine similarity)")
    ax.set_title("Figure 12 - Distribucion de scores SPECTER por PB sobre los 31k abstracts",
                 loc="left", weight="bold")
    ax.text(0, 1.02,
            "Violins muestran como discrimina el modelo cada PB. Ancho = densidad, linea = mediana.",
            transform=ax.transAxes, fontsize=10, color="#666", style="italic")
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
    ax.set_axisbelow(True)
    save(fig, "12_score_distribution_specter")

# ---------------------------------------------------------------------------
# Figure 13 - model agreement on full corpus
# ---------------------------------------------------------------------------
print("\n[fig 13] model agreement on full corpus")

top1 = {}
common = None
for m, pa in preds_all.items():
    s = pa.set_index("doc_id")["pred_top1"]
    top1[MODEL_SHORT[m]] = s
    common = s.index if common is None else common.intersection(s.index)

models_short = list(top1)
agree = pd.DataFrame(index=models_short, columns=models_short, dtype=float)
for a in models_short:
    for b in models_short:
        agree.loc[a, b] = (top1[a].loc[common] == top1[b].loc[common]).mean()
agree.to_csv(TAB / "model_agreement_full.csv")

fig, ax = plt.subplots(figsize=(7, 6))
sns.heatmap(agree.astype(float), annot=True, fmt=".2f", cmap="Greens",
            vmin=0.0, vmax=1.0, linewidths=0.5, linecolor="white", ax=ax,
            cbar_kws=dict(label="acuerdo top-1"))
ax.set_title(f"Figure 13 - Acuerdo cruzado top-1 sobre {len(common):,} abstracts",
             loc="left", weight="bold")
save(fig, "13_model_agreement_full")


# ---------------------------------------------------------------------------
# Summary JSON
# ---------------------------------------------------------------------------
print("\n[summary] writing metrics_summary.json")

best_micro = max(metrics_json.items(),
                 key=lambda kv: kv[1].get("threshold_delta", {}).get("micro_f1", 0))
best_macro = max(metrics_json.items(),
                 key=lambda kv: kv[1].get("threshold_delta", {}).get("macro_f1", 0))

summary = {
    "n_corpus_predicted": int(len(preds_all[list(preds_all)[0]])),
    "n_validation": int(len(preds_val[list(preds_val)[0]])),
    "models": {
        MODEL_SHORT[m]: {
            "top1": mj["top1"],
            "threshold_delta": mj.get("threshold_delta", {}),
        } for m, mj in metrics_json.items()
    },
    "best_micro_f1": {"model": MODEL_SHORT[best_micro[0]],
                      "value": best_micro[1].get("threshold_delta", {}).get("micro_f1")},
    "best_macro_f1": {"model": MODEL_SHORT[best_macro[0]],
                      "value": best_macro[1].get("threshold_delta", {}).get("macro_f1")},
    "agreement_specter_vs_others": agree["specter"].to_dict() if "specter" in agree.columns else {},
}
(AED / "metrics_summary.json").write_text(json.dumps(summary, indent=2, default=str))
print(f"  -> {(AED/'metrics_summary.json').relative_to(ROOT)}")
print("\n[done]")
