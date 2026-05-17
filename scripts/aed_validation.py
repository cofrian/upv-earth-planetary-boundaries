"""
Validacion cabeza a cabeza de la muestra anotada (n=99 con gold no vacio)
contra los 6 modelos.

Genera:
  docs/eda/aed/figures/14_validation_perdoc.png      heatmap doc x modelo (hit/partial/miss)
  docs/eda/aed/figures/15_confusion_per_model.png    matriz de confusion (multilabel) por modelo
  docs/eda/aed/figures/16_error_taxonomy.png         distribucion de tipos de error por modelo
  docs/eda/aed/tables/validation_perdoc.csv          tabla maestra: doc | titulo | gold | preds | hits
  docs/eda/aed/tables/error_taxonomy.csv
  docs/eda/aed/tables/confusion_pairs.csv
"""
from __future__ import annotations

import re
import json
from pathlib import Path
from itertools import product

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nlp/bert_finetuning/outputs_full"
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
AED = ROOT / "docs/eda/aed"
FIG = AED / "figures"
TAB = AED / "tables"

PB_CODES = [f"PB{i}" for i in range(1, 10)]
PB_NAMES = {"PB1":"Climate","PB2":"Ocean","PB3":"Ozone","PB4":"Biogeochem",
            "PB5":"Freshwater","PB6":"Land-Sys","PB7":"Biosphere",
            "PB8":"Novel","PB9":"Aerosol"}
PB_COLORS = {"PB1":"#1F4E79","PB2":"#3F7CAC","PB3":"#6BAED6","PB9":"#9ECAE1",
             "PB5":"#2E7D32","PB6":"#558B2F","PB7":"#81C784",
             "PB4":"#D26F3D","PB8":"#B53A1E"}
MODELS = [
    ("baseline_lexical", "lexical"),
    ("baseline_semantic_tfidf", "tfidf"),
    ("backbone_bert_base_uncased", "bert-base"),
    ("backbone_roberta_base", "roberta"),
    ("backbone_allenai_scibert_scivocab_uncased", "scibert"),
    ("backbone_allenai_specter", "specter"),
]

mpl.rcParams.update({
    "figure.dpi":130, "savefig.dpi":300, "savefig.bbox":"tight",
    "font.family":"DejaVu Sans", "font.size":10,
    "axes.titlesize":12, "axes.titleweight":"bold",
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


# ---------------------------------------------------------------------------
# Load predictions and gold
# ---------------------------------------------------------------------------
print("[load] validation predictions")
val = {}
for folder, short in MODELS:
    p = OUT / folder / "predictions_validation.csv"
    df = pd.read_csv(p)
    df = df[df["gold_labels"].notna() & (df["gold_labels"].astype(str).str.len() > 0)].copy()
    df["gold_set"] = df["gold_labels"].map(parse_label_set)
    df["top1_set"] = df["pred_top1"].map(lambda x: {x} if pd.notna(x) and x in PB_CODES else set())
    df["multi_set"] = df["pred_multilabel"].map(parse_label_set)
    df = df.drop_duplicates(subset=["doc_id"], keep="first")
    val[short] = df.set_index("doc_id")
    print(f"  {short}: {len(df)} docs annotated")

# Common doc set
common_ids = None
for short, df in val.items():
    common_ids = set(df.index) if common_ids is None else common_ids & set(df.index)
common_ids = sorted(common_ids)
print(f"  common ids = {len(common_ids)}")

# Titles
print("[load] corpus titles")
corpus = pd.read_csv(CORPUS, usecols=["doc_id", "title"], low_memory=False)
titles = corpus.set_index("doc_id")["title"].to_dict()

# ---------------------------------------------------------------------------
# Build master per-doc table
# ---------------------------------------------------------------------------
print("\n[build] per-doc table")
rows = []
short_names = [s for _, s in MODELS]

for did in common_ids:
    gold = val[short_names[0]].loc[did, "gold_set"]
    row = {
        "doc_id": did,
        "title": (str(titles.get(did) or "")[:120]) if not pd.isna(titles.get(did)) else "",
        "gold": ",".join(sorted(gold)),
        "n_gold": len(gold),
    }
    for s in short_names:
        pred_top1 = val[s].loc[did, "top1_set"]
        pred_multi = val[s].loc[did, "multi_set"]
        # Verdict on top1
        if pred_top1 == set():
            v1 = "miss"
        elif pred_top1 & gold:
            v1 = "hit"
        else:
            v1 = "miss"
        # Verdict on multilabel
        if not pred_multi:
            vm = "miss"
        elif pred_multi == gold:
            vm = "exact"
        elif pred_multi & gold:
            n_correct = len(pred_multi & gold)
            n_extra = len(pred_multi - gold)
            n_miss = len(gold - pred_multi)
            if n_extra == 0 and n_miss == 0:
                vm = "exact"
            elif n_extra > 0 and n_miss == 0:
                vm = "over"      # predijo de mas
            elif n_extra == 0 and n_miss > 0:
                vm = "under"     # predijo de menos
            else:
                vm = "partial"   # mezcla
        else:
            vm = "miss"
        row[f"{s}_top1"] = ",".join(sorted(pred_top1))
        row[f"{s}_top1_verdict"] = v1
        row[f"{s}_multi"] = ",".join(sorted(pred_multi))
        row[f"{s}_multi_verdict"] = vm
    rows.append(row)

per_doc = pd.DataFrame(rows)
per_doc.to_csv(TAB / "validation_perdoc.csv", index=False)
print(f"  -> {(TAB/'validation_perdoc.csv').relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# Figure 14 - per-doc heatmap
# ---------------------------------------------------------------------------
print("\n[fig 14] per-doc validation heatmap")

# Build verdict matrix (rows=docs, cols=models). top1 verdict.
verdict_to_int = {"hit": 2, "exact": 2, "partial": 1, "over": 1, "under": 1, "miss": 0}
order_cols = short_names

# sort docs by gold then by total hits
per_doc["_hits"] = per_doc[[f"{s}_top1_verdict" for s in order_cols]].apply(
    lambda r: sum(v == "hit" for v in r), axis=1
)
per_doc_sorted = per_doc.sort_values(["gold", "_hits"], ascending=[True, False]).reset_index(drop=True)

mat = np.zeros((len(per_doc_sorted), len(order_cols)), dtype=int)
for i, r in per_doc_sorted.iterrows():
    for j, s in enumerate(order_cols):
        mat[i, j] = verdict_to_int[r[f"{s}_top1_verdict"]]

fig, axes = plt.subplots(1, 2, figsize=(14, 11),
                         gridspec_kw=dict(width_ratios=[1, 3.5], wspace=0.03))

# Left: gold annotation strip
ax = axes[0]
gold_strip = np.zeros((len(per_doc_sorted), 9), dtype=int)
for i, r in per_doc_sorted.iterrows():
    glabels = parse_label_set(r["gold"])
    for j, pb in enumerate(PB_CODES):
        if pb in glabels:
            gold_strip[i, j] = 1
ax.imshow(gold_strip, aspect="auto", cmap="Greys", vmin=0, vmax=1.4, interpolation="nearest")
ax.set_xticks(range(9))
ax.set_xticklabels(PB_CODES, fontsize=7)
ax.set_yticks([])
ax.set_title("gold labels", loc="left", fontsize=10)

# Right: model verdicts
ax = axes[1]
cmap = mpl.colors.ListedColormap(["#d63a3a", "#f4b400", "#2e8b57"])  # miss / partial / hit
norm = mpl.colors.BoundaryNorm([0, 1, 2, 3], cmap.N)
ax.imshow(mat, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
ax.set_xticks(range(len(order_cols)))
ax.set_xticklabels(order_cols, rotation=20, ha="right", fontsize=10)
ax.set_yticks([])
ax.set_title("Top-1 verdict per model (red=miss, yellow=partial, green=hit)",
             loc="left", fontsize=10)
# Hit rate at column header
for j, s in enumerate(order_cols):
    hr = (mat[:, j] == 2).mean()
    ax.text(j, -1.5, f"{hr*100:.0f}%", ha="center", fontsize=10,
            color="#1F4E79", weight="bold")

fig.suptitle(f"Figure 14 - Validacion top-1 documento a documento (n={len(per_doc_sorted)} con gold)",
             fontsize=13, weight="bold", x=0.04, ha="left", y=0.99)
fig.text(0.04, 0.965,
         "Cada fila = un abstract anotado manualmente; columnas = modelos. "
         "Las cifras encima de cada columna son hit-rate top-1.",
         fontsize=9.5, color="#666", style="italic")
save(fig, "14_validation_perdoc")

# ---------------------------------------------------------------------------
# Figure 15 - PB confusion per model (multilabel: where do FPs/FNs land?)
# ---------------------------------------------------------------------------
print("\n[fig 15] PB confusion per model")

# For each model: for each gold label, distribution of predicted labels (top1)
fig, axes = plt.subplots(2, 3, figsize=(17, 10), gridspec_kw=dict(wspace=0.28, hspace=0.45))
axes = axes.flatten()

for ax, (folder, short) in zip(axes, MODELS):
    df = val[short].loc[common_ids]
    # confusion: rows = gold PB, cols = predicted top1 PB
    conf = pd.DataFrame(0, index=PB_CODES, columns=PB_CODES, dtype=int)
    for _, r in df.iterrows():
        gold = r["gold_set"]; pred = r["top1_set"]
        if not pred:
            continue
        ptop = next(iter(pred))
        for g in gold:
            conf.loc[g, ptop] += 1
    # Normalize rows
    conf_norm = conf.div(conf.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    sns.heatmap(conf_norm, ax=ax, cmap="Blues", vmin=0, vmax=1,
                annot=conf.values, fmt="d",
                annot_kws=dict(fontsize=7), cbar=False,
                linewidths=0.3, linecolor="white")
    ax.set_title(short, loc="left", fontsize=12, weight="bold")
    ax.set_xlabel("predicted top-1"); ax.set_ylabel("gold PB")
    ax.set_xticklabels(PB_CODES, fontsize=8)
    ax.set_yticklabels(PB_CODES, fontsize=8, rotation=0)

fig.suptitle("Figure 15 - Matriz de confusion top-1 (gold -> prediccion) por modelo",
             fontsize=14, weight="bold", x=0.04, ha="left", y=1.0)
fig.text(0.04, 0.97,
         "Diagonal = aciertos. Filas que se vacian fuera de la diagonal son confusiones recurrentes.",
         fontsize=10, color="#666", style="italic")
save(fig, "15_confusion_per_model")

# Save top confusion pairs across all models
conf_rows = []
for folder, short in MODELS:
    df = val[short].loc[common_ids]
    for _, r in df.iterrows():
        gold = r["gold_set"]; pred = r["top1_set"]
        if not pred: continue
        ptop = next(iter(pred))
        for g in gold:
            if g != ptop:
                conf_rows.append({"model": short, "gold": g, "predicted": ptop})
conf_df = pd.DataFrame(conf_rows)
top_conf = (conf_df.groupby(["model","gold","predicted"]).size()
            .reset_index(name="count").sort_values(["model","count"], ascending=[True, False]))
top_conf.to_csv(TAB / "confusion_pairs.csv", index=False)

# ---------------------------------------------------------------------------
# Figure 16 - error taxonomy
# ---------------------------------------------------------------------------
print("\n[fig 16] error taxonomy")

# Per model, classify multilabel verdict
tax_rows = []
verdicts = ["exact", "over", "under", "partial", "miss"]
for short in short_names:
    counts = per_doc[f"{short}_multi_verdict"].value_counts().reindex(verdicts, fill_value=0)
    total = counts.sum()
    for v in verdicts:
        tax_rows.append({"model": short, "verdict": v, "count": int(counts[v]),
                         "pct": float(counts[v]/total*100)})
tax = pd.DataFrame(tax_rows)
tax.to_csv(TAB / "error_taxonomy.csv", index=False)

fig, ax = plt.subplots(figsize=(11, 5.5))
colors = {"exact":"#2e8b57", "over":"#9b59b6", "under":"#e67e22",
          "partial":"#f4b400", "miss":"#d63a3a"}
piv = tax.pivot(index="model", columns="verdict", values="pct").reindex(
    index=short_names, columns=verdicts)
bottom = np.zeros(len(piv))
for v in verdicts:
    ax.barh(piv.index, piv[v].values, left=bottom, color=colors[v],
            edgecolor="white", linewidth=0.6, label=v)
    bottom += piv[v].values
# Annotate exact rate at the end
for i, m in enumerate(piv.index):
    exact_pct = piv.loc[m, "exact"]
    ax.text(101, i, f" exact = {exact_pct:.0f}%", va="center",
            fontsize=9.5, color="#2e8b57", weight="bold")
ax.set_xlim(0, 115)
ax.set_xlabel("% de docs anotados")
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=9.5,
          handletextpad=0.4)
ax.set_title("Figure 16 - Taxonomia de errores multilabel por modelo",
             loc="left", weight="bold")
ax.text(0, 1.03,
        "exact = igualan el set; over = predicen de mas; under = se quedan cortos; "
        "partial = solapamiento parcial; miss = sin interseccion.",
        transform=ax.transAxes, fontsize=9.5, color="#666", style="italic")
save(fig, "16_error_taxonomy")

# ---------------------------------------------------------------------------
# Per-model summary
# ---------------------------------------------------------------------------
print("\n[summary] validation report")
summary_rows = []
for short in short_names:
    df = per_doc
    n = len(df)
    hit1 = (df[f"{short}_top1_verdict"]=="hit").sum()
    exact = (df[f"{short}_multi_verdict"]=="exact").sum()
    over = (df[f"{short}_multi_verdict"]=="over").sum()
    under = (df[f"{short}_multi_verdict"]=="under").sum()
    partial = (df[f"{short}_multi_verdict"]=="partial").sum()
    miss = (df[f"{short}_multi_verdict"]=="miss").sum()
    summary_rows.append({
        "model": short,
        "n_docs": n,
        "top1_hit_rate": round(hit1/n, 3),
        "multi_exact_rate": round(exact/n, 3),
        "multi_overall_overlap_rate": round((exact+over+under+partial)/n, 3),
        "multi_miss_rate": round(miss/n, 3),
        "exact": int(exact), "over": int(over), "under": int(under),
        "partial": int(partial), "miss": int(miss),
    })
summary = pd.DataFrame(summary_rows)
summary.to_csv(TAB / "validation_summary.csv", index=False)
print(summary.to_string(index=False))

# Markdown export
(AED / "validation_perdoc_preview.md").write_text(
    "# Vista previa de validacion (primeros 30 docs)\n\n"
    + per_doc_sorted.head(30)[[
        "doc_id","title","gold",
        "specter_top1","specter_multi_verdict",
        "tfidf_top1","tfidf_multi_verdict",
        "scibert_top1","bert-base_top1","roberta_top1","lexical_top1",
    ]].to_markdown(index=False)
)
print("\n[done]")
