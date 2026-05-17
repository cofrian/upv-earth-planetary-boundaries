"""
AED maestro UPV-EARTH x Planetary Boundaries.

Produce todas las figuras y tablas del AED en docs/eda/aed/{figures,tables}/
y un eda_narrative.md con interpretacion.

Inputs:
  data/corpus/master_corpus_mixto_clean_enriched.csv   (corpus completo, 31634 docs)
  nlp/bert_finetuning/outputs/backbone_allenai_specter/predictions_all_docs.csv  (PB labels)
  nlp/bert_finetuning/outputs/<otros backbones>/predictions_all_docs.csv         (model compare)
  corpus_PB/data/pb_reference.csv                                                (definiciones PB)

Run: python scripts/aed_master.py
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch, Wedge, Circle
from matplotlib.lines import Line2D
import seaborn as sns

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths and style
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
_OUT = ROOT / "nlp/bert_finetuning/outputs_full"
SPECTER = _OUT / "backbone_allenai_specter/predictions_all_docs.csv"
BACKBONES = {
    "specter": _OUT / "backbone_allenai_specter/predictions_all_docs.csv",
    "scibert": _OUT / "backbone_allenai_scibert_scivocab_uncased/predictions_all_docs.csv",
    "bert-base": _OUT / "backbone_bert_base_uncased/predictions_all_docs.csv",
    "roberta": _OUT / "backbone_roberta_base/predictions_all_docs.csv",
    "lex-baseline": _OUT / "baseline_lexical/predictions_all_docs.csv",
    "tfidf-baseline": _OUT / "baseline_semantic_tfidf/predictions_all_docs.csv",
}
PB_REF = ROOT / "corpus_PB/data/pb_reference.csv"

OUT = ROOT / "docs/eda/aed"
FIG = OUT / "figures"
TAB = OUT / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

PB_CODES = [f"PB{i}" for i in range(1, 10)]
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
PB_FAMILY = {
    "PB1": "Atmosphere & Climate",
    "PB2": "Atmosphere & Climate",
    "PB3": "Atmosphere & Climate",
    "PB9": "Atmosphere & Climate",
    "PB5": "Land, Water & Biosphere",
    "PB6": "Land, Water & Biosphere",
    "PB7": "Land, Water & Biosphere",
    "PB4": "Chemical & Biogeochemical Pressure",
    "PB8": "Chemical & Biogeochemical Pressure",
}
FAMILY_COLORS = {
    "Atmosphere & Climate": "#3F7CAC",
    "Land, Water & Biosphere": "#3E8E5A",
    "Chemical & Biogeochemical Pressure": "#D26F3D",
}
PB_COLORS = {
    "PB1": "#1F4E79", "PB2": "#3F7CAC", "PB3": "#6BAED6", "PB9": "#9ECAE1",
    "PB5": "#2E7D32", "PB6": "#558B2F", "PB7": "#81C784",
    "PB4": "#D26F3D", "PB8": "#B53A1E",
}

mpl.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
    "axes.titlesize": 12.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 10.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
    "xtick.color": "#444444",
    "ytick.color": "#444444",
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "axes.titlepad": 12,
    "axes.labelpad": 6,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "figure.facecolor": "white",
})

SAVE_KW = dict(dpi=300, bbox_inches="tight", facecolor="white")


def save(fig, name):
    p_png = FIG / f"{name}.png"
    p_pdf = FIG / f"{name}.pdf"
    fig.savefig(p_png, **SAVE_KW)
    fig.savefig(p_pdf, **SAVE_KW)
    plt.close(fig)
    print(f"  -> {p_png.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
print("[load] corpus + predictions")
corpus = pd.read_csv(CORPUS, low_memory=False)
corpus["year"] = pd.to_numeric(corpus["year"], errors="coerce")
corpus = corpus[(corpus["year"].isna()) | ((corpus["year"] >= 1980) & (corpus["year"] <= 2025))]

preds = {}
for name, path in BACKBONES.items():
    if path.exists():
        df = pd.read_csv(path, low_memory=False, on_bad_lines="skip")
        df = df.dropna(subset=["pred_top1"])
        df = df[df["pred_top1"].isin(PB_CODES)]
        preds[name] = df
        print(f"  preds[{name}]: {len(df)} rows")

specter = preds["specter"].copy()
specter = specter.merge(
    corpus[["doc_id", "year", "journal", "source", "abstract_norm_len"]],
    on="doc_id", how="left"
)
print(f"  specter joined: {len(specter)} rows, year null = {specter['year'].isna().sum()}")

# Parse multilabel
specter["multilabel_list"] = specter["pred_multilabel"].fillna("").apply(
    lambda s: [x for x in str(s).split(",") if x.startswith("PB")]
)
# If empty multilabel, fall back to top1 for distribution analysis
specter["labels_effective"] = specter.apply(
    lambda r: r["multilabel_list"] if r["multilabel_list"] else [r["pred_top1"]],
    axis=1
)

# ---------------------------------------------------------------------------
# Helper: paper-style ax decoration
# ---------------------------------------------------------------------------
def style_ax(ax, title=None, subtitle=None, ygrid=True):
    if title:
        ax.set_title(title, loc="left")
    if subtitle:
        ax.text(0.0, 1.02, subtitle, transform=ax.transAxes,
                fontsize=9.5, color="#666666", style="italic", ha="left")
    if ygrid:
        ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
        ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Section 1 - corpus traceability + temporal + length
# ---------------------------------------------------------------------------
print("\n[fig 01] corpus overview panel")

# Read traceability if exists for the flow numbers
trace_csv = ROOT / "data/corpus/master_corpus_mixto_traceability.csv"
flow_numbers = {"raw": None, "merged": 44970, "deduplicated": 44593, "filtered": 31634}
if trace_csv.exists():
    t = pd.read_csv(trace_csv, low_memory=False)
    flow_numbers["raw"] = len(t)
    if "kept" in t.columns:
        flow_numbers["filtered"] = int(t["kept"].sum())

fig = plt.figure(figsize=(14, 9))
gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.35)

# (a) Corpus flow
ax = fig.add_subplot(gs[0, 0])
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
stages = [
    ("Raw Scopus + OpenAlex", flow_numbers.get("raw") or "~46k", "#e0e0e0"),
    ("Merged corpus", flow_numbers["merged"], "#cfd8dc"),
    ("Deduplicated", flow_numbers["deduplicated"], "#90a4ae"),
    ("Final corpus", flow_numbers["filtered"], "#1F4E79"),
]
y = 9
for label, n, color in stages:
    ax.add_patch(FancyBboxPatch((1.0, y-1.4), 8, 1.3, boxstyle="round,pad=0.05",
                                 linewidth=0, facecolor=color))
    txt_color = "white" if color in ("#1F4E79", "#90a4ae") else "#222"
    ax.text(5, y-0.45, label, ha="center", va="center", fontsize=10, color=txt_color, weight="bold")
    ax.text(5, y-0.95, f"N = {n:,}" if isinstance(n, int) else f"N = {n}",
            ha="center", va="center", fontsize=9.5, color=txt_color)
    if y > 3:
        ax.annotate("", xy=(5, y-1.7), xytext=(5, y-1.4),
                    arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.2))
    y -= 2.1
ax.set_title("a. Corpus construction flow", loc="left", weight="bold")

# (b) Publications per year
ax = fig.add_subplot(gs[0, 1:])
ypub = corpus.dropna(subset=["year"]).copy()
ypub["year"] = ypub["year"].astype(int)
ypub = ypub[(ypub["year"] >= 1990) & (ypub["year"] <= 2024)]
yc = ypub.groupby("year").size()
ax.fill_between(yc.index, yc.values, color="#1F4E79", alpha=0.18)
ax.plot(yc.index, yc.values, color="#1F4E79", lw=2)
# annotate peak
peak_y = yc.idxmax(); peak_v = yc.max()
ax.annotate(f"peak {peak_y}: {peak_v:,}", xy=(peak_y, peak_v),
            xytext=(peak_y-12, peak_v*0.9),
            arrowprops=dict(arrowstyle="->", color="#666"), fontsize=9, color="#444")
ax.set_xlabel("Year"); ax.set_ylabel("Publications")
style_ax(ax, "b. Temporal evolution of UPV-EARTH corpus",
         f"{int(yc.sum()):,} abstracts, 1990-2024")

# (c) Abstract length histogram
ax = fig.add_subplot(gs[1, 0])
lens = corpus["abstract_norm_len"].dropna()
lens = lens[(lens > 0) & (lens < 5000)]
ax.hist(lens, bins=60, color="#3F7CAC", edgecolor="white", linewidth=0.4)
ax.axvline(lens.median(), color="#B53A1E", lw=1.2, linestyle="--",
           label=f"median = {int(lens.median())}")
ax.legend(loc="upper right")
ax.set_xlabel("abstract length (chars)"); ax.set_ylabel("docs")
style_ax(ax, "c. Abstract length distribution")

# (d) Completeness heatmap
ax = fig.add_subplot(gs[1, 1])
cols_q = ["year", "doi", "journal", "keywords", "authors", "abstract_norm"]
miss = (corpus[cols_q].isna().mean() * 100).round(2)
ax.barh(miss.index[::-1], miss.values[::-1], color="#9E9E9E", edgecolor="white")
for i, v in enumerate(miss.values[::-1]):
    ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9, color="#444")
ax.set_xlabel("% missing"); ax.set_xlim(0, max(miss.max()*1.2, 5))
style_ax(ax, "d. Metadata completeness", ygrid=False)
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

# (e) Source distribution (if exists)
ax = fig.add_subplot(gs[1, 2])
sources = corpus["source"].fillna("unknown").value_counts().head(6)
colors = plt.cm.Blues(np.linspace(0.45, 0.85, len(sources)))
ax.barh(sources.index[::-1], sources.values[::-1], color=colors[::-1], edgecolor="white")
for i, v in enumerate(sources.values[::-1]):
    ax.text(v, i, f" {v:,}", va="center", fontsize=9, color="#333")
ax.set_xlabel("docs")
style_ax(ax, "e. Corpus by source", ygrid=False)
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

fig.suptitle("Figure 1 - UPV-EARTH corpus overview",
             fontsize=15, weight="bold", x=0.06, ha="left", y=1.0)
fig.text(0.06, 0.96,
         f"N = {len(corpus):,} cleaned abstracts | 1990-2024 | sources: Scopus + OpenAlex",
         fontsize=10, color="#666", style="italic")
save(fig, "01_corpus_overview")


# ---------------------------------------------------------------------------
# Section 2 - PB profile radial (the "signature")
# ---------------------------------------------------------------------------
print("\n[fig 02] PB radial signature")

# Use multilabel for the profile (each PB appearance counts)
all_labels = [pb for lst in specter["labels_effective"] for pb in lst]
pb_counts = pd.Series(all_labels).value_counts().reindex(PB_CODES, fill_value=0)
pb_pct = (pb_counts / pb_counts.sum() * 100).round(2)
pb_counts.to_csv(TAB / "pb_distribution_specter.csv", header=["count"])

fig = plt.figure(figsize=(15.8, 8.8), facecolor="white")
gs = fig.add_gridspec(1, 2, width_ratios=[1.65, 1], wspace=0.14)

short_pb_labels = {
    "PB1": "Climate",
    "PB2": "Ocean",
    "PB3": "Ozone",
    "PB4": "BioGeo",
    "PB5": "Freshwater",
    "PB6": "Land-System",
    "PB7": "Biosphere",
    "PB8": "Novel",
    "PB9": "Aerosol",
}

# (a) Radial bar plot with planet-like background
ax = fig.add_subplot(gs[0, 0], projection="polar")
ax.set_facecolor("#eaf3fb")
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)

n = len(PB_CODES)
angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
width = 2 * np.pi / n * 0.85
values = pb_pct.values
max_v = max(values.max() * 1.15, 5)

bars = ax.bar(angles, values, width=width,
              color=[PB_COLORS[c] for c in PB_CODES],
              edgecolor="white", linewidth=1.5, zorder=3)

# Background "planet" rings
for r in np.linspace(0, max_v, 5)[1:]:
    ax.plot(np.linspace(0, 2*np.pi, 200), [r]*200,
            color="#c8d8e6", lw=0.5, alpha=0.7, zorder=1)

# Central planet
ax.set_ylim(0, max_v)
ax.set_yticklabels([])
ax.set_xticks(angles)
ax.set_xticklabels([f"{c}\n{short_pb_labels[c]}" for c in PB_CODES],
                   fontsize=10, color="#333", fontweight="semibold")
ax.tick_params(pad=12)
ax.grid(False)
ax.spines["polar"].set_visible(False)

# Value labels at the tip of each bar
for ang, val, code in zip(angles, values, PB_CODES):
    ax.text(ang, val + max_v*0.05, f"{val:.1f}%", ha="center", va="center",
            fontsize=10, color=PB_COLORS[code], weight="bold", zorder=5)

# Central disc with summary
ax.text(0, -max_v*0.18, "UPV-EARTH", ha="center", va="center",
        fontsize=12, weight="bold", color="#1F4E79", transform=ax.transData)
# Title and subtitle outside
fig.suptitle("Planetary boundary profile of UPV scientific production",
             fontsize=17, weight="bold", color="#1F4E79", x=0.03, y=0.975, ha="left")
fig.text(0.03, 0.935,
         f"{int(pb_counts.sum()):,} PB assignments across {len(specter):,} labeled abstracts "
         f"(SPECTER, multilabel).",
         fontsize=10.5, color="#667", style="italic")

# (b) Side ranking
ax2 = fig.add_subplot(gs[0, 1])
ax2.axis("off")
ranked = pb_pct.sort_values(ascending=False)
ax2.set_xlim(0, 1)
ax2.text(0, 0.98, "Ranking by share", fontsize=15, weight="bold",
         color="#1F4E79", transform=ax2.transAxes)
ax2.text(0, 0.945, "PB code and full planetary boundary name",
         fontsize=9.5, color="#667", transform=ax2.transAxes)
y = 0.875
for i, (code, v) in enumerate(ranked.items()):
    bar_w = v / ranked.max() * 0.76
    ax2.add_patch(plt.Rectangle((0.0, y-0.021), bar_w, 0.024,
                                color=PB_COLORS[code], transform=ax2.transAxes))
    ax2.text(0.0, y+0.018, f"{code} - {PB_NAMES[code]}",
             fontsize=10.5, color="#333", transform=ax2.transAxes, va="bottom")
    ax2.text(min(bar_w + 0.012, 0.79), y-0.008, f"{v:.1f}%",
             fontsize=10.5, color=PB_COLORS[code], weight="bold", transform=ax2.transAxes)
    y -= 0.095

# Legend of families
y_leg = 0.065
ax2.text(0, y_leg+0.055, "PB families", fontsize=10.5, weight="bold", color="#1F4E79",
         transform=ax2.transAxes)
for fam, col in FAMILY_COLORS.items():
    members = ", ".join([c for c, f in PB_FAMILY.items() if f == fam])
    ax2.add_patch(plt.Rectangle((0.0, y_leg-0.015), 0.025, 0.025,
                                color=col, transform=ax2.transAxes))
    ax2.text(0.04, y_leg, f"{fam} ({members})", fontsize=8.8, color="#444",
             transform=ax2.transAxes, va="center")
    y_leg -= 0.035

save(fig, "02_pb_radial_signature")


# ---------------------------------------------------------------------------
# Section 3 - cooccurrence heatmap and network
# ---------------------------------------------------------------------------
print("\n[fig 03/04] PB cooccurrence")

co = pd.DataFrame(0, index=PB_CODES, columns=PB_CODES, dtype=float)
for lst in specter["labels_effective"]:
    uniq = sorted(set(lst))
    for a in uniq:
        co.loc[a, a] += 1
    for a, b in combinations(uniq, 2):
        co.loc[a, b] += 1
        co.loc[b, a] += 1

# Jaccard
jaccard = pd.DataFrame(0.0, index=PB_CODES, columns=PB_CODES)
for a in PB_CODES:
    for b in PB_CODES:
        if a == b:
            jaccard.loc[a, b] = 1.0
        else:
            inter = co.loc[a, b]
            union = co.loc[a, a] + co.loc[b, b] - inter
            jaccard.loc[a, b] = inter / union if union > 0 else 0
co.to_csv(TAB / "pb_cooccurrence.csv")
jaccard.to_csv(TAB / "pb_jaccard.csv")

fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw=dict(wspace=0.25))

# Heatmap raw cooccurrence (upper triangle masked diag)
ax = axes[0]
mask = np.eye(len(PB_CODES), dtype=bool)
sns.heatmap(co.mask(mask), ax=ax, cmap="Blues", annot=True, fmt=".0f",
            linewidths=0.5, linecolor="white", cbar_kws=dict(label="papers"),
            annot_kws=dict(fontsize=8.5, color="#222"))
ax.set_title("a. Raw co-occurrence (papers sharing two PBs)", loc="left", weight="bold")

# Heatmap Jaccard
ax = axes[1]
sns.heatmap(jaccard.mask(mask), ax=ax, cmap="OrRd", annot=True, fmt=".2f",
            vmin=0, vmax=jaccard.mask(mask).values.max() if jaccard.mask(mask).values.max() > 0 else 1,
            linewidths=0.5, linecolor="white", cbar_kws=dict(label="Jaccard"),
            annot_kws=dict(fontsize=8.5))
ax.set_title("b. Normalized association (Jaccard)", loc="left", weight="bold")

fig.suptitle("Figure 3 - Systemic interaction between Planetary Boundaries",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
fig.text(0.05, 0.97,
         "Raw counts highlight where research overlaps; Jaccard corrects for category size.",
         fontsize=10, color="#666", style="italic")
save(fig, "03_pb_cooccurrence_heatmaps")

# Network
print("[fig 04] PB network")
import networkx as nx
G = nx.Graph()
for c in PB_CODES:
    G.add_node(c, size=int(co.loc[c, c]))
for a, b in combinations(PB_CODES, 2):
    w = jaccard.loc[a, b]
    if w > 0:
        G.add_edge(a, b, weight=float(w), raw=int(co.loc[a, b]))

fig, ax = plt.subplots(figsize=(10, 8))
ax.set_facecolor("#fafafa")
pos = nx.spring_layout(G, weight="weight", seed=7, k=1.2/np.sqrt(len(G)))
sizes = np.array([G.nodes[n]["size"] for n in G.nodes])
node_sizes = 400 + (sizes - sizes.min()) / max(1, (sizes.max() - sizes.min())) * 2800
node_colors = [PB_COLORS[n] for n in G.nodes]

edges = list(G.edges(data=True))
weights = np.array([d["weight"] for *_, d in edges])
edge_w = 0.5 + (weights - weights.min()) / max(1e-9, (weights.max() - weights.min())) * 6
edge_alpha = 0.25 + 0.65 * (weights - weights.min()) / max(1e-9, (weights.max() - weights.min()))
for (u, v, d), w, a in zip(edges, edge_w, edge_alpha):
    ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
            lw=w, color="#5a7d99", alpha=a, zorder=1)

for n, s, c in zip(G.nodes, node_sizes, node_colors):
    ax.scatter(*pos[n], s=s, color=c, edgecolor="white", linewidth=2, zorder=3)
    ax.text(pos[n][0], pos[n][1], n, ha="center", va="center",
            fontsize=9.5, color="white", weight="bold", zorder=4)

# Centralities
deg_w = dict(nx.degree(G, weight="weight"))
btw = nx.betweenness_centrality(G, weight=lambda u, v, d: 1 - d["weight"])
cent_df = pd.DataFrame({
    "pb": list(G.nodes),
    "weighted_degree": [deg_w[n] for n in G.nodes],
    "betweenness": [btw[n] for n in G.nodes],
}).sort_values("weighted_degree", ascending=False)
cent_df.to_csv(TAB / "pb_network_centrality.csv", index=False)

ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Figure 4 - PB co-occurrence network",
             loc="left", weight="bold", fontsize=14)
ax.text(0, 1.02,
        "Node size = PB frequency in corpus; edge thickness/opacity = Jaccard association.",
        transform=ax.transAxes, fontsize=10, color="#666", style="italic")
save(fig, "04_pb_network")


# ---------------------------------------------------------------------------
# Section 4 - temporal PB heatmap (year x PB)
# ---------------------------------------------------------------------------
print("\n[fig 05] temporal PB heatmap")

sp_y = specter.dropna(subset=["year"]).copy()
sp_y["year"] = sp_y["year"].astype(int)
sp_y = sp_y[(sp_y["year"] >= 1995) & (sp_y["year"] <= 2024)]
sp_y["bucket"] = pd.cut(
    sp_y["year"],
    bins=[1994, 2000, 2005, 2010, 2015, 2020, 2025],
    labels=["1995-2000", "2001-2005", "2006-2010", "2011-2015", "2016-2020", "2021-2024"]
)

# expand multilabel
rows = []
for _, r in sp_y.iterrows():
    for pb in r["labels_effective"]:
        rows.append({"bucket": r["bucket"], "year": r["year"], "pb": pb})
sp_long = pd.DataFrame(rows)

# year x PB normalized (% of each year)
yr_pb = sp_long.groupby(["year", "pb"]).size().unstack(fill_value=0).reindex(columns=PB_CODES, fill_value=0)
yr_pb_pct = (yr_pb.div(yr_pb.sum(axis=1).replace(0, np.nan), axis=0) * 100).fillna(0)
yr_pb_pct.to_csv(TAB / "pb_share_per_year.csv")

fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.5), gridspec_kw=dict(width_ratios=[2, 1], wspace=0.3))

ax = axes[0]
sns.heatmap(yr_pb_pct.T.reindex(PB_CODES), ax=ax, cmap="YlGnBu",
            cbar_kws=dict(label="% of yearly PB-assignments"),
            linewidths=0)
ax.set_xlabel("Year"); ax.set_ylabel("")
ax.set_yticklabels([f"{c} - {PB_NAMES[c]}" for c in PB_CODES], rotation=0)
ax.set_title("a. Year x PB share heatmap", loc="left", weight="bold")

# slope chart by period
ax = axes[1]
slope_df = sp_long.groupby(["bucket", "pb"]).size().unstack(fill_value=0).reindex(columns=PB_CODES, fill_value=0)
slope_pct = slope_df.div(slope_df.sum(axis=1).replace(0, np.nan), axis=0) * 100
slope_pct.to_csv(TAB / "pb_share_per_bucket.csv")

periods = slope_pct.index.tolist()
xs = np.arange(len(periods))
for code in PB_CODES:
    vals = slope_pct[code].values
    ax.plot(xs, vals, "-o", color=PB_COLORS[code], lw=1.6, markersize=4.5, alpha=0.85)
    ax.text(xs[-1] + 0.05, vals[-1], code, fontsize=8.5, color=PB_COLORS[code],
            weight="bold", va="center")
ax.set_xticks(xs); ax.set_xticklabels(periods, rotation=30, ha="right")
ax.set_ylabel("% of period PB-assignments")
style_ax(ax, "b. PB share evolution by period")

fig.suptitle("Figure 5 - Temporal evolution of the UPV-EARTH PB profile",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
fig.text(0.05, 0.97,
         "Reads the changing emphasis of UPV research over time, normalized per year/period.",
         fontsize=10, color="#666", style="italic")
save(fig, "05_pb_temporal")


# ---------------------------------------------------------------------------
# Section 5 - multilabelity
# ---------------------------------------------------------------------------
print("\n[fig 06] multilabel distribution")

mlc = specter["pred_multilabel_count"].fillna(0).astype(int)
ml_dist = mlc.value_counts().sort_index()

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw=dict(wspace=0.3))

ax = axes[0]
colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(ml_dist)))
bars = ax.bar(ml_dist.index.astype(str), ml_dist.values, color=colors, edgecolor="white")
for b, v in zip(bars, ml_dist.values):
    ax.text(b.get_x()+b.get_width()/2, v + ml_dist.max()*0.01, f"{v}",
            ha="center", fontsize=9.5, color="#333", weight="bold")
ax.set_xlabel("# PBs per paper"); ax.set_ylabel("papers")
style_ax(ax, "a. How many Planetary Boundaries does each paper touch?",
         f"mean = {mlc.mean():.2f} | median = {int(mlc.median())} | papers >=2 PB = {(mlc>=2).sum()} ({(mlc>=2).mean()*100:.1f}%)")

# Per-PB: % of its papers that appear alone vs combined
ax = axes[1]
alone = {c: 0 for c in PB_CODES}
combined = {c: 0 for c in PB_CODES}
for lst in specter["labels_effective"]:
    if len(lst) == 1:
        alone[lst[0]] += 1
    else:
        for pb in lst:
            combined[pb] += 1
df_ac = pd.DataFrame({"alone": alone, "combined": combined}).reindex(PB_CODES)
df_ac["total"] = df_ac.sum(axis=1)
df_ac["pct_combined"] = df_ac["combined"] / df_ac["total"] * 100
df_ac = df_ac.sort_values("pct_combined")
ax.barh(df_ac.index, df_ac["pct_combined"], color=[PB_COLORS[c] for c in df_ac.index],
        edgecolor="white")
for i, (c, v) in enumerate(df_ac["pct_combined"].items()):
    ax.text(v+1, i, f"{v:.0f}%", va="center", fontsize=9, color="#333")
ax.set_xlim(0, 105)
ax.set_xlabel("% of PB papers co-occurring with other PBs")
ax.set_yticklabels([f"{c}" for c in df_ac.index])
style_ax(ax, "b. Systemic vs isolated PBs", ygrid=False)
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)

fig.suptitle("Figure 6 - Multi-label structure of PB assignments",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
save(fig, "06_pb_multilabel")
df_ac.to_csv(TAB / "pb_alone_vs_combined.csv")


# ---------------------------------------------------------------------------
# Section 6 - semantic UMAP colored by top1 PB
# ---------------------------------------------------------------------------
print("\n[fig 07] semantic UMAP")

# Build embeddings from PB score vectors (lightweight semantic proxy)
score_cols = [f"score_{c}" for c in PB_CODES]
X = specter[score_cols].fillna(0).values
# Normalize
from sklearn.preprocessing import normalize
Xn = normalize(X)
import umap
reducer = umap.UMAP(n_neighbors=15, min_dist=0.15, metric="cosine", random_state=42)
emb = reducer.fit_transform(Xn)

fig, ax = plt.subplots(figsize=(11, 8))
ax.set_facecolor("#fafafa")
for code in PB_CODES:
    mask = specter["pred_top1"].values == code
    ax.scatter(emb[mask, 0], emb[mask, 1], s=30, color=PB_COLORS[code],
               edgecolor="white", linewidth=0.4, alpha=0.85,
               label=f"{code} - {PB_NAMES[code]}")

# Annotate cluster centroids
for code in PB_CODES:
    mask = specter["pred_top1"].values == code
    if mask.sum() < 5:
        continue
    cx, cy = emb[mask, 0].mean(), emb[mask, 1].mean()
    ax.text(cx, cy, code, fontsize=11, weight="bold", color="#222",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=PB_COLORS[code], lw=1.2, alpha=0.9))

ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=9)
ax.set_title("Figure 7 - Semantic map of UPV abstracts (UMAP over PB score vectors)",
             loc="left", weight="bold", fontsize=14)
ax.text(0, 1.02,
        "Each point is an abstract; colour = SPECTER top-1 PB. "
        "Tight clusters indicate well-separated PB themes; mixed zones reveal systemic overlap.",
        transform=ax.transAxes, fontsize=9.5, color="#666", style="italic")
save(fig, "07_semantic_umap")


# ---------------------------------------------------------------------------
# Section 7 - model comparison
# ---------------------------------------------------------------------------
print("\n[fig 08] model comparison")

# Build top1 per model on shared doc_ids
common_ids = None
top1 = {}
for name, df in preds.items():
    s = df.set_index("doc_id")["pred_top1"]
    top1[name] = s
    common_ids = s.index if common_ids is None else common_ids.intersection(s.index)

models = list(top1.keys())
agree = pd.DataFrame(index=models, columns=models, dtype=float)
for a in models:
    for b in models:
        sa = top1[a].loc[common_ids]
        sb = top1[b].loc[common_ids]
        agree.loc[a, b] = (sa == sb).mean()
agree.to_csv(TAB / "model_agreement.csv")

# Coverage per PB per model
cov_rows = []
for name, df in preds.items():
    counts = df["pred_top1"].value_counts().reindex(PB_CODES, fill_value=0)
    pct = counts / counts.sum() * 100
    for pb, v in pct.items():
        cov_rows.append({"model": name, "pb": pb, "pct": v})
cov_df = pd.DataFrame(cov_rows)

fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1.1, 1.4], wspace=0.35))

ax = axes[0]
sns.heatmap(agree.astype(float), annot=True, fmt=".2f", cmap="Greens",
            vmin=0.2, vmax=1.0, ax=ax, linewidths=0.5, linecolor="white",
            cbar_kws=dict(label="top-1 agreement"))
ax.set_title("a. Cross-model top-1 agreement", loc="left", weight="bold")

ax = axes[1]
piv = cov_df.pivot(index="model", columns="pb", values="pct").reindex(columns=PB_CODES)
piv = piv.loc[models]
bottom = np.zeros(len(piv))
for code in PB_CODES:
    vals = piv[code].values
    ax.barh(piv.index, vals, left=bottom, color=PB_COLORS[code],
            edgecolor="white", linewidth=0.6, label=code)
    bottom += vals
ax.set_xlabel("% of labels per model")
ax.set_xlim(0, 100)
ax.legend(ncol=9, loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=8.5,
          handletextpad=0.4, columnspacing=0.8)
ax.set_title("b. PB coverage by model", loc="left", weight="bold")

fig.suptitle("Figure 8 - Model behaviour: agreement and PB coverage",
             fontsize=14, weight="bold", x=0.05, ha="left", y=1.02)
save(fig, "08_model_comparison")


# ---------------------------------------------------------------------------
# Section 8 - Summary tables and JSON for narrative
# ---------------------------------------------------------------------------
print("\n[summary] aggregating numbers")

n_corpus = int(len(corpus))
n_labeled = int(len(specter))
year_min = int(corpus["year"].dropna().min())
year_max = int(corpus["year"].dropna().max())
peak_year = int(yc.idxmax()); peak_v = int(yc.max())

top_pbs = pb_pct.sort_values(ascending=False).head(3)
bot_pbs = pb_pct.sort_values().head(3)

# Top Jaccard pairs
pairs = []
for a, b in combinations(PB_CODES, 2):
    pairs.append((a, b, float(jaccard.loc[a, b]), int(co.loc[a, b])))
pairs.sort(key=lambda x: -x[2])
top_pairs = pairs[:5]

summary = {
    "n_corpus": n_corpus,
    "n_pb_labeled": n_labeled,
    "year_range": [year_min, year_max],
    "peak_year": peak_year,
    "peak_value": peak_v,
    "median_abstract_len": int(lens.median()),
    "pb_distribution_pct": pb_pct.to_dict(),
    "top_pbs": top_pbs.to_dict(),
    "bottom_pbs": bot_pbs.to_dict(),
    "multilabel_share_ge2": float((mlc >= 2).mean()),
    "mean_pbs_per_paper": float(mlc.mean()),
    "top_jaccard_pairs": [
        {"a": a, "b": b, "jaccard": j, "papers": n} for a, b, j, n in top_pairs
    ],
    "centrality": cent_df.head(5).to_dict(orient="records"),
    "model_agreement": agree.round(3).to_dict(),
    "completeness_missing_pct": miss.to_dict(),
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
print(f"  -> {(OUT/'summary.json').relative_to(ROOT)}")
print("\n[done]")
