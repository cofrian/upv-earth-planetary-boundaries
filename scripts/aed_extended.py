"""
AED extendido: figuras faltantes del plan AED_PLAN.md + JSON por figura.

Anyade:
  21. Lollipop ranking PB
  22. Treemap por familias PB
  23. Stacked area temporal absoluto
  24. Streamgraph normalizado (% por anyo)
  25. Radial doble capa (1990-2015 vs 2016-2024)
  26. Small multiples por periodo (3 radials)
  27. Cards de ejemplos representativos
  28. Sankey topics -> PBs (KMeans sobre TF-IDF score vectors)
  29. Top journals por PB

Para cada figura exporta JSON plot-ready en docs/eda/aed/data_json/
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from itertools import combinations
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch, Rectangle
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
ASSIGN = ROOT / "data/corpus/pb_assignments_top3.csv"
TFIDF_PRED = ROOT / "nlp/bert_finetuning/outputs_full/baseline_semantic_tfidf/predictions_all_docs.csv"

AED = ROOT / "docs/eda/aed"
FIG = AED / "figures"
TAB = AED / "tables"
JSON = AED / "data_json"
FIG.mkdir(parents=True, exist_ok=True)
JSON.mkdir(parents=True, exist_ok=True)

PB_CODES = [f"PB{i}" for i in range(1, 10)]
SCORE_COLS = [f"score_{c}" for c in PB_CODES]
PB_NAMES = {
    "PB1": "Climate Change", "PB2": "Ocean Acidification",
    "PB3": "Stratospheric Ozone", "PB4": "Biogeochemical Flows",
    "PB5": "Freshwater Use", "PB6": "Land-System Change",
    "PB7": "Biosphere Integrity", "PB8": "Novel Entities",
    "PB9": "Aerosol Loading",
}
PB_FAMILY = {
    "PB1": "Atmosphere & Climate", "PB2": "Atmosphere & Climate",
    "PB3": "Atmosphere & Climate", "PB9": "Atmosphere & Climate",
    "PB5": "Land, Water & Biosphere", "PB6": "Land, Water & Biosphere",
    "PB7": "Land, Water & Biosphere",
    "PB4": "Chemical & Biogeochemical", "PB8": "Chemical & Biogeochemical",
}
FAMILY_COLORS = {
    "Atmosphere & Climate": "#3F7CAC",
    "Land, Water & Biosphere": "#3E8E5A",
    "Chemical & Biogeochemical": "#D26F3D",
}
PB_COLORS = {
    "PB1": "#1F4E79", "PB2": "#3F7CAC", "PB3": "#6BAED6", "PB9": "#9ECAE1",
    "PB5": "#2E7D32", "PB6": "#558B2F", "PB7": "#81C784",
    "PB4": "#D26F3D", "PB8": "#B53A1E",
}

mpl.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 10.5,
    "axes.titlesize": 12.5, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#444", "xtick.color": "#444", "ytick.color": "#444",
    "axes.titlepad": 12, "legend.frameon": False, "figure.facecolor": "white",
})

SAVE_KW = dict(dpi=300, bbox_inches="tight", facecolor="white")


def save_fig(fig, name):
    fig.savefig(FIG / f"{name}.png", **SAVE_KW)
    fig.savefig(FIG / f"{name}.pdf", **SAVE_KW)
    plt.close(fig)
    print(f"  -> {(FIG/f'{name}.png').relative_to(ROOT)}")


def save_json(name, data):
    p = JSON / f"{name}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=float))
    print(f"  -> {p.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
print("[load]")
co = pd.read_csv(CORPUS, low_memory=False)
co["year"] = pd.to_numeric(co["year"], errors="coerce")
co = co[(co["year"].isna()) | ((co["year"] >= 1980) & (co["year"] <= 2025))]
pr = pd.read_csv(TFIDF_PRED, low_memory=False)
df = pr.merge(co[["doc_id", "year", "journal", "source"]], on="doc_id", how="left")
df["year_int"] = df["year"].astype("Int64")

# Multilabel set
def parse_set(v):
    if pd.isna(v) or v == "": return set()
    return set(re.findall(r"PB\d+", str(v)))
df["multi_set"] = df["pred_multilabel"].map(parse_set)
# fallback to top1 if multi empty
df["labels_effective"] = df.apply(
    lambda r: r["multi_set"] if r["multi_set"] else {r["pred_top1"]} if r["pred_top1"] in PB_CODES else set(),
    axis=1
)

# All PB-labels expanded
all_labels = [pb for s in df["labels_effective"] for pb in s]
pb_counts = pd.Series(all_labels).value_counts().reindex(PB_CODES, fill_value=0)
pb_pct = (pb_counts / pb_counts.sum() * 100).round(2)

n_total = len(df)
print(f"  {n_total:,} papers")

# ---------------------------------------------------------------------------
# Figure 21 - Lollipop ranking
# ---------------------------------------------------------------------------
print("\n[fig 21] lollipop PB ranking")

ranked = pb_pct.sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(11, 6))
for i, (code, v) in enumerate(ranked.items()):
    color = PB_COLORS[code]
    ax.plot([0, v], [i, i], color=color, lw=2.5, alpha=0.6, zorder=1)
    ax.scatter(v, i, s=240, color=color, edgecolor="white", linewidth=2, zorder=2)
    ax.text(v + 0.4, i, f"{v:.1f}%  ({int(pb_counts[code]):,})",
            va="center", fontsize=9.5, color=color, weight="bold")
    ax.text(-0.4, i, f"{code}  {PB_NAMES[code]}", va="center", ha="right",
            fontsize=10, color="#333")

ax.set_yticks([]); ax.set_xlim(-9, max(pb_pct.values) * 1.18)
ax.set_xlabel("% del corpus PB-related")
ax.spines["left"].set_visible(False)
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("Figure 21 - Ranking de PBs en la produccion UPV-EARTH",
             loc="left", weight="bold", fontsize=14)
ax.text(0, 1.04, f"N = {n_total:,} papers | metodo: TF-IDF multilabel",
        transform=ax.transAxes, fontsize=10, color="#666", style="italic")
save_fig(fig, "21_lollipop_ranking")
save_json("21_lollipop_ranking", {
    "n_total_papers": int(n_total),
    "method": "TF-IDF multilabel + top1 fallback",
    "ranking": [
        {"pb": c, "name": PB_NAMES[c], "family": PB_FAMILY[c],
         "count": int(pb_counts[c]), "pct_of_labels": float(pb_pct[c])}
        for c in PB_CODES
    ],
})


# ---------------------------------------------------------------------------
# Figure 22 - Treemap PB families
# ---------------------------------------------------------------------------
print("\n[fig 22] treemap PB families")

try:
    import squarify
    has_squarify = True
except ImportError:
    has_squarify = False
    print("  squarify no instalado, usando layout manual")

# Aggregate by family
fam_counts = {}
for c in PB_CODES:
    fam_counts.setdefault(PB_FAMILY[c], []).append((c, int(pb_counts[c])))

sizes = []
labels = []
colors = []
for fam, lst in fam_counts.items():
    for code, n in sorted(lst, key=lambda x: -x[1]):
        sizes.append(n)
        labels.append(f"{code}\n{PB_NAMES[code]}\n{n:,}\n({pb_pct[code]}%)")
        colors.append(PB_COLORS[code])

fig, ax = plt.subplots(figsize=(13, 7.5))
if has_squarify:
    squarify.plot(sizes=sizes, label=labels, color=colors, ax=ax,
                  text_kwargs={"fontsize": 10, "color": "white", "weight": "bold"},
                  edgecolor="white", linewidth=2.5, alpha=0.92)
else:
    # Simple grid fallback
    n = len(sizes); ncols = 3; nrows = 3
    for i, (s, l, c) in enumerate(zip(sizes, labels, colors)):
        r, c_i = i // ncols, i % ncols
        ax.add_patch(Rectangle((c_i, nrows-1-r), 1, 1, facecolor=c, edgecolor="white"))
        ax.text(c_i+0.5, nrows-1-r+0.5, l, ha="center", va="center",
                fontsize=9, color="white", weight="bold")
    ax.set_xlim(0, ncols); ax.set_ylim(0, nrows)

ax.axis("off")
ax.set_title("Figure 22 - Treemap PB families: huella tematica de la UPV por familia",
             loc="left", weight="bold", fontsize=14)

# Family legend
y_leg = -0.05
fig.text(0.04, 0.04, "Familias:", fontsize=10, weight="bold", color="#1F4E79")
x = 0.16
for fam, col in FAMILY_COLORS.items():
    fig.patches.append(Rectangle((x, 0.04), 0.018, 0.025, transform=fig.transFigure,
                                   facecolor=col))
    fig.text(x+0.025, 0.045, fam, fontsize=9.5, color="#444")
    x += 0.25

save_fig(fig, "22_treemap_families")
save_json("22_treemap_families", {
    "n_total_labels": int(pb_counts.sum()),
    "families": {
        fam: {
            "members": [m[0] for m in lst],
            "total_labels": sum(m[1] for m in lst),
            "share_of_pb_labels": round(sum(m[1] for m in lst) / pb_counts.sum() * 100, 2),
        } for fam, lst in fam_counts.items()
    },
    "items": [
        {"pb": c, "name": PB_NAMES[c], "family": PB_FAMILY[c], "count": int(pb_counts[c])}
        for c in PB_CODES
    ],
})


# ---------------------------------------------------------------------------
# Figure 23 - Stacked area absolute (papers per year by PB)
# ---------------------------------------------------------------------------
print("\n[fig 23] stacked area temporal absoluto")

dt = df.dropna(subset=["year"]).copy()
dt["year"] = dt["year"].astype(int)
dt = dt[(dt["year"] >= 1995) & (dt["year"] <= 2024)]
rows = []
for _, r in dt.iterrows():
    for pb in r["labels_effective"]:
        rows.append({"year": r["year"], "pb": pb})
yr_pb = pd.DataFrame(rows).groupby(["year", "pb"]).size().unstack(fill_value=0).reindex(columns=PB_CODES, fill_value=0)

fig, ax = plt.subplots(figsize=(13, 6.5))
years = yr_pb.index.values
ys = [yr_pb[c].values for c in PB_CODES]
colors_o = [PB_COLORS[c] for c in PB_CODES]
ax.stackplot(years, ys, labels=PB_CODES, colors=colors_o, edgecolor="white", linewidth=0.4)
ax.set_xlabel("Year"); ax.set_ylabel("# PB-assignments (multilabel expanded)")
ax.legend(loc="upper left", fontsize=9, ncol=3)
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("Figure 23 - Crecimiento absoluto del corpus PB por anyo",
             loc="left", weight="bold", fontsize=14)
ax.text(0, 1.02, "Cada banda = # de asignaciones PB en ese anyo (multilabel expandido).",
        transform=ax.transAxes, fontsize=10, color="#666", style="italic")
save_fig(fig, "23_stacked_area_absolute")
save_json("23_stacked_area_absolute", {
    "x_label": "year",
    "y_label": "n_pb_assignments",
    "years": years.tolist(),
    "series": {c: yr_pb[c].astype(int).tolist() for c in PB_CODES},
})


# ---------------------------------------------------------------------------
# Figure 24 - Streamgraph normalizado (% per year by PB)
# ---------------------------------------------------------------------------
print("\n[fig 24] streamgraph normalizado")

yr_pct = yr_pb.div(yr_pb.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100

fig, ax = plt.subplots(figsize=(13, 6))
ys = [yr_pct[c].values for c in PB_CODES]
ax.stackplot(years, ys, labels=PB_CODES, colors=colors_o,
             edgecolor="white", linewidth=0.4)
ax.set_xlabel("Year"); ax.set_ylabel("% de asignaciones PB del anyo")
ax.set_ylim(0, 100)
ax.legend(loc="upper left", fontsize=9, ncol=3, bbox_to_anchor=(1.01, 1.0))
ax.set_title("Figure 24 - Evolucion relativa del perfil PB (normalizada por anyo)",
             loc="left", weight="bold", fontsize=14)
ax.text(0, 1.02, "Corrige el crecimiento global del corpus: aqui se ve cambio de agenda.",
        transform=ax.transAxes, fontsize=10, color="#666", style="italic")
save_fig(fig, "24_streamgraph_normalized")
save_json("24_streamgraph_normalized", {
    "x_label": "year",
    "y_label": "pct_of_yearly_pb_assignments",
    "years": years.tolist(),
    "series": {c: yr_pct[c].round(3).tolist() for c in PB_CODES},
})


# ---------------------------------------------------------------------------
# Figure 25 - Radial double layer (1990-2015 vs 2016-2024)
# ---------------------------------------------------------------------------
print("\n[fig 25] radial doble capa")

def pb_pct_period(yfrom, yto):
    d = dt[(dt["year"] >= yfrom) & (dt["year"] <= yto)]
    labels = [pb for s in d["labels_effective"] for pb in s]
    s = pd.Series(labels).value_counts().reindex(PB_CODES, fill_value=0)
    return (s / s.sum() * 100).round(2) if s.sum() else s

pct_hist = pb_pct_period(1995, 2015)
pct_rec = pb_pct_period(2016, 2024)
n_hist = sum((dt["year"] >= 1995) & (dt["year"] <= 2015))
n_rec = sum((dt["year"] >= 2016) & (dt["year"] <= 2024))

fig = plt.figure(figsize=(11, 9))
ax = fig.add_subplot(111, projection="polar")
ax.set_facecolor("#eaf3fb")
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
angles = np.linspace(0, 2*np.pi, len(PB_CODES), endpoint=False)
width = 2*np.pi/len(PB_CODES)*0.38

max_v = max(pct_hist.max(), pct_rec.max()) * 1.15

# Inner ring (historical) - left half of each sector
ax.bar(angles - width/2, pct_hist.values, width=width,
       color=[PB_COLORS[c] for c in PB_CODES], edgecolor="white", linewidth=1.5,
       alpha=0.7, zorder=2, label="1995-2015")
# Outer ring (recent)
ax.bar(angles + width/2, pct_rec.values, width=width,
       color=[PB_COLORS[c] for c in PB_CODES], edgecolor="white", linewidth=1.5,
       alpha=1.0, zorder=3, label="2016-2024")

for r in np.linspace(0, max_v, 5)[1:]:
    ax.plot(np.linspace(0, 2*np.pi, 200), [r]*200, color="#c8d8e6", lw=0.5, alpha=0.7)

ax.set_ylim(0, max_v); ax.set_yticklabels([])
ax.set_xticks(angles)
ax.set_xticklabels([f"{c}\n{PB_NAMES[c].split()[0]}" for c in PB_CODES], fontsize=9)
ax.grid(False); ax.spines["polar"].set_visible(False)
ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.05))

# Annotate change
for ang, code in zip(angles, PB_CODES):
    delta = pct_rec[code] - pct_hist[code]
    sign = "+" if delta >= 0 else ""
    col = "#2e8b57" if delta > 0 else ("#d63a3a" if delta < -0.5 else "#888")
    ax.text(ang, max_v*0.97, f"{sign}{delta:.1f}",
            ha="center", va="center", fontsize=8, color=col, weight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=col, lw=0.6, alpha=0.9))

fig.text(0.5, 0.94,
         "Figure 25 - Firma PB: anillo interior 1995-2015 vs exterior 2016-2024",
         fontsize=13, weight="bold", ha="center", color="#1F4E79")
fig.text(0.5, 0.91,
         f"N hist={n_hist:,}  N reciente={n_rec:,} | numeros = delta % (verde=crece, rojo=decrece)",
         fontsize=9.5, color="#666", style="italic", ha="center")
save_fig(fig, "25_radial_doublelayer")
save_json("25_radial_doublelayer", {
    "period_historic": {"from": 1995, "to": 2015, "n_papers": int(n_hist)},
    "period_recent": {"from": 2016, "to": 2024, "n_papers": int(n_rec)},
    "data": [
        {"pb": c, "name": PB_NAMES[c],
         "pct_historic": float(pct_hist[c]),
         "pct_recent": float(pct_rec[c]),
         "delta_pp": round(float(pct_rec[c] - pct_hist[c]), 2)}
        for c in PB_CODES
    ],
})

# ---------------------------------------------------------------------------
# Figure 26 - Small multiples por periodo
# ---------------------------------------------------------------------------
print("\n[fig 26] small multiples")

periods = [("1995-2005", 1995, 2005), ("2006-2015", 2006, 2015), ("2016-2024", 2016, 2024)]
fig = plt.figure(figsize=(15, 5.5))
all_period_data = {}
for i, (lab, y1, y2) in enumerate(periods):
    pct = pb_pct_period(y1, y2)
    n = sum((dt["year"] >= y1) & (dt["year"] <= y2))
    all_period_data[lab] = {"n_papers": int(n),
                             "pct_by_pb": {c: float(pct[c]) for c in PB_CODES}}
    ax = fig.add_subplot(1, 3, i+1, projection="polar")
    ax.set_facecolor("#eaf3fb")
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    angs = np.linspace(0, 2*np.pi, len(PB_CODES), endpoint=False)
    ax.bar(angs, pct.values, width=2*np.pi/len(PB_CODES)*0.85,
           color=[PB_COLORS[c] for c in PB_CODES], edgecolor="white", linewidth=1.2)
    mx = max(pct_hist.max(), pct_rec.max()) * 1.15
    ax.set_ylim(0, mx); ax.set_yticklabels([])
    ax.set_xticks(angs)
    ax.set_xticklabels(PB_CODES, fontsize=8)
    ax.grid(False); ax.spines["polar"].set_visible(False)
    ax.set_title(f"{lab}\nN={n:,}", fontsize=11, weight="bold", color="#1F4E79", pad=14)

fig.suptitle("Figure 26 - Evolucion de la firma PB por periodos",
             fontsize=14, weight="bold", x=0.5, ha="center", y=1.05)
save_fig(fig, "26_radial_small_multiples")
save_json("26_radial_small_multiples", all_period_data)


# ---------------------------------------------------------------------------
# Figure 27 - Cards de ejemplos representativos
# ---------------------------------------------------------------------------
print("\n[fig 27] cards ejemplos representativos")

# Para cada PB pick 1 ejemplo con score alto y margen claro
co_titles = co.set_index("doc_id")["title"].to_dict()
co_abs = co.set_index("doc_id")["abstract"].to_dict() if "abstract" in co.columns else {}

cards = []
for c in PB_CODES:
    sub = df.copy()
    sub = sub[sub["pred_top1"] == c]
    if sub.empty: continue
    score_col = f"score_{c}"
    sub = sub.sort_values(score_col, ascending=False)
    pick = sub.iloc[0]
    title = co_titles.get(pick["doc_id"], "")
    if pd.isna(title) or not title: title = "(sin titulo)"
    abst = co_abs.get(pick["doc_id"], "")
    if isinstance(abst, str) and len(abst) > 240:
        abst = abst[:240].rsplit(" ", 1)[0] + "..."
    cards.append({
        "pb": c, "pb_name": PB_NAMES[c],
        "doc_id": pick["doc_id"],
        "title": str(title)[:120],
        "abstract_excerpt": str(abst)[:240] if isinstance(abst, str) else "",
        "score_top1": round(float(pick[score_col]), 4),
        "top2": pick["pred_top2"],
        "score_top2": round(float(pick[f"score_{pick['pred_top2']}" ]),4) if pick["pred_top2"] in PB_CODES else None,
    })

fig, axes = plt.subplots(3, 3, figsize=(17, 11))
axes = axes.flatten()
for ax, card in zip(axes, cards):
    ax.axis("off")
    ax.set_facecolor("#f7f9fc")
    col = PB_COLORS[card["pb"]]
    ax.add_patch(Rectangle((0, 0.85), 1, 0.15, facecolor=col, transform=ax.transAxes))
    ax.text(0.04, 0.92, f"{card['pb']}  -  {card['pb_name']}",
            transform=ax.transAxes, fontsize=11, color="white", weight="bold")
    ax.text(0.04, 0.78, card["title"][:90] + ("..." if len(card["title"])>90 else ""),
            transform=ax.transAxes, fontsize=9.5, color="#222", weight="bold", wrap=True)
    abs_text = card["abstract_excerpt"]
    # word wrap
    if abs_text:
        words = abs_text.split()
        lines = []; cur = ""
        for w in words:
            if len(cur) + len(w) > 60:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur: lines.append(cur)
        for i, l in enumerate(lines[:5]):
            ax.text(0.04, 0.66 - i*0.085, l, transform=ax.transAxes,
                    fontsize=8.5, color="#444")
    ax.text(0.04, 0.13, f"score top-1: {card['score_top1']:.4f}",
            transform=ax.transAxes, fontsize=8.5, color=col, weight="bold")
    ax.text(0.04, 0.05,
            f"top-2: {card['top2']} ({card['score_top2']:.4f})" if card['score_top2'] else "",
            transform=ax.transAxes, fontsize=8.5, color="#666")
    # border
    for s in ["bottom","top","left","right"]:
        ax.spines[s].set_visible(False)
    ax.add_patch(Rectangle((0,0), 1, 1, transform=ax.transAxes,
                            facecolor="none", edgecolor="#dddddd", linewidth=1))

fig.suptitle("Figure 27 - Ejemplos representativos por PB (top-1 mas confiado)",
             fontsize=14, weight="bold", x=0.04, ha="left", y=0.995)
save_fig(fig, "27_cards_examples")
save_json("27_cards_examples", {"cards": cards})


# ---------------------------------------------------------------------------
# Figure 28 - Sankey topics (KMeans) -> PBs
# ---------------------------------------------------------------------------
print("\n[fig 28] Sankey topics -> PBs (KMeans sobre score vectors)")

from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

X = df[SCORE_COLS].fillna(0).values
Xn = normalize(X)
K = 8
km = KMeans(n_clusters=K, random_state=42, n_init=10).fit(Xn)
df["cluster"] = km.labels_

# Label clusters by dominant PBs (top-2 PBs por cluster)
cluster_labels = {}
for k in range(K):
    centroid = km.cluster_centers_[k]
    top_pbs = np.argsort(-centroid)[:2]
    cluster_labels[k] = f"T{k+1}: " + "+".join(PB_CODES[i] for i in top_pbs)

# Build flow cluster -> top1 PB
flows = []
for k in range(K):
    sub = df[df["cluster"] == k]
    n_k = len(sub)
    top1_dist = sub["pred_top1"].value_counts()
    for pb in PB_CODES:
        n = int(top1_dist.get(pb, 0))
        if n > 50:  # filter small flows
            flows.append({"source": k, "source_label": cluster_labels[k],
                          "target": pb, "n": n})

# Plot manual Sankey
fig, ax = plt.subplots(figsize=(13, 8))
ax.axis("off")

# Position clusters on left, PBs on right
left_x = 0.15; right_x = 0.85
cluster_sizes = df["cluster"].value_counts().reindex(range(K)).fillna(0).values
total = cluster_sizes.sum()
cluster_y = []
y = 0.95
for k in range(K):
    h = cluster_sizes[k] / total * 0.85
    cluster_y.append((y - h, y))
    y -= h + 0.01

pb_sizes = df["pred_top1"].value_counts().reindex(PB_CODES, fill_value=0).values
pb_y = []
y = 0.95
for i, c in enumerate(PB_CODES):
    h = pb_sizes[i] / total * 0.85
    pb_y.append((y - h, y))
    y -= h + 0.01

# Draw nodes
for k in range(K):
    y0, y1 = cluster_y[k]
    ax.add_patch(Rectangle((left_x-0.07, y0), 0.07, y1-y0,
                           facecolor="#888", edgecolor="white"))
    ax.text(left_x-0.08, (y0+y1)/2, cluster_labels[k],
            ha="right", va="center", fontsize=9, color="#333")

for i, c in enumerate(PB_CODES):
    y0, y1 = pb_y[i]
    ax.add_patch(Rectangle((right_x, y0), 0.07, y1-y0,
                           facecolor=PB_COLORS[c], edgecolor="white"))
    ax.text(right_x+0.08, (y0+y1)/2, f"{c} ({int(pb_sizes[i]):,})",
            ha="left", va="center", fontsize=9, color="#333")

# Track usage per side
cluster_used = {k: cluster_y[k][1] for k in range(K)}
pb_used = {c: pb_y[i][1] for i, c in enumerate(PB_CODES)}

# Draw flows (curved)
for f in sorted(flows, key=lambda x: -x["n"]):
    k = f["source"]; c = f["target"]
    fr = f["n"] / total * 0.85
    y_src_top = cluster_used[k]
    y_src_bot = y_src_top - fr
    cluster_used[k] = y_src_bot - 0.001
    pb_i = PB_CODES.index(c)
    y_tgt_top = pb_used[c]
    y_tgt_bot = y_tgt_top - fr
    pb_used[c] = y_tgt_bot - 0.001
    # Bezier polygon
    n_pts = 30
    t = np.linspace(0, 1, n_pts)
    xs = left_x + (right_x - left_x) * t
    cx = 0.5
    # top curve
    yt_top = (1-t)**2 * y_src_top + 2*(1-t)*t * y_src_top + t**2 * y_tgt_top
    yt_bot = (1-t)**2 * y_src_bot + 2*(1-t)*t * y_src_bot + t**2 * y_tgt_bot
    # smoother
    s = (1 - np.cos(t * np.pi)) / 2
    yt_top = (1-s) * y_src_top + s * y_tgt_top
    yt_bot = (1-s) * y_src_bot + s * y_tgt_bot
    ax.fill_between(xs, yt_bot, yt_top, color=PB_COLORS[c], alpha=0.35, linewidth=0)

ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("Figure 28 - Sankey de topics latentes (KMeans) hacia PBs",
             loc="left", weight="bold", fontsize=14)
ax.text(0, 1.02,
        f"8 clusters semanticos sobre score-vectors TF-IDF, conectados al pred_top1 (filtro >50 papers).",
        transform=ax.transAxes, fontsize=10, color="#666", style="italic")
save_fig(fig, "28_sankey_topics_pbs")
save_json("28_sankey_topics_pbs", {
    "n_clusters": K,
    "cluster_centers_top_pbs": [
        {"cluster": k, "label": cluster_labels[k],
         "top_pbs": [PB_CODES[i] for i in np.argsort(-km.cluster_centers_[k])[:3]],
         "n_papers": int(cluster_sizes[k])} for k in range(K)
    ],
    "flows": flows,
})


# ---------------------------------------------------------------------------
# Figure 29 - Top journals por PB
# ---------------------------------------------------------------------------
print("\n[fig 29] top journals por PB")

dj = df[df["journal"].notna() & (df["journal"] != "")].copy()
dj["journal"] = dj["journal"].astype(str).str.strip().str[:60]
# Top 20 journals overall
top_jrnls = dj["journal"].value_counts().head(20).index.tolist()
dj_top = dj[dj["journal"].isin(top_jrnls)].copy()

# expand multilabel
rows = []
for _, r in dj_top.iterrows():
    for pb in r["labels_effective"]:
        rows.append({"journal": r["journal"], "pb": pb})
jrnl_pb = pd.DataFrame(rows).groupby(["journal", "pb"]).size().unstack(fill_value=0).reindex(columns=PB_CODES, fill_value=0)
# Order journals by total
jrnl_pb = jrnl_pb.loc[jrnl_pb.sum(axis=1).sort_values(ascending=False).index]

fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(jrnl_pb, ax=ax, cmap="YlGnBu", annot=True, fmt="d", linewidths=0.3,
            linecolor="white", cbar_kws=dict(label="# PB-assignments"),
            annot_kws=dict(fontsize=8))
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels([f"{c}\n{PB_NAMES[c]}" for c in PB_CODES], rotation=0, fontsize=8.5)
ax.set_title("Figure 29 - Top 20 journals UPV: distribucion por PB",
             loc="left", weight="bold", fontsize=14)
save_fig(fig, "29_journals_by_pb")
save_json("29_journals_by_pb", {
    "top_n_journals": 20,
    "matrix": jrnl_pb.astype(int).to_dict(orient="index"),
})


# ---------------------------------------------------------------------------
# Re-export JSON for the existing key figures (read from tables)
# ---------------------------------------------------------------------------
print("\n[json] exporting data for figures 02-08")

# Fig 02: radial signature (PB distribution)
save_json("02_pb_radial_signature", {
    "method": "TF-IDF multilabel + top1 fallback",
    "n_total_papers": int(n_total),
    "data": [{"pb": c, "name": PB_NAMES[c], "family": PB_FAMILY[c],
              "count": int(pb_counts[c]), "pct": float(pb_pct[c])} for c in PB_CODES]
})

# Fig 03/04: cooccurrence
co_mat = pd.DataFrame(0, index=PB_CODES, columns=PB_CODES, dtype=int)
for s in df["labels_effective"]:
    s = sorted(s)
    for a in s: co_mat.loc[a, a] += 1
    for a, b in combinations(s, 2):
        co_mat.loc[a, b] += 1; co_mat.loc[b, a] += 1
jac = pd.DataFrame(0.0, index=PB_CODES, columns=PB_CODES)
for a in PB_CODES:
    for b in PB_CODES:
        if a == b: jac.loc[a, b] = 1.0
        else:
            inter = co_mat.loc[a, b]
            uni = co_mat.loc[a, a] + co_mat.loc[b, b] - inter
            jac.loc[a, b] = inter / uni if uni > 0 else 0
save_json("03_pb_cooccurrence", {
    "raw_counts": co_mat.astype(int).to_dict(),
    "jaccard": jac.round(3).to_dict(),
    "top_pairs_jaccard": sorted(
        [{"a": a, "b": b, "jaccard": float(jac.loc[a,b]), "count": int(co_mat.loc[a,b])}
         for a, b in combinations(PB_CODES, 2)],
        key=lambda x: -x["jaccard"]
    )[:10]
})

# Fig 06: multilabel
mlc = df["pred_multilabel_count"].fillna(0).astype(int).value_counts().sort_index()
save_json("06_pb_multilabel", {
    "n_total": int(n_total),
    "mean_pbs_per_paper": float(df["pred_multilabel_count"].fillna(0).mean()),
    "distribution_count": {int(k): int(v) for k, v in mlc.items()},
})

# Fig 09/10: metrics + per-PB F1 (read from existing tables)
metrics_path = AED / "metrics_summary.json"
if metrics_path.exists():
    msj = json.loads(metrics_path.read_text())
    save_json("09_metrics_overview", msj["models"])

per_pb_csv = TAB / "per_pb_metrics.csv"
if per_pb_csv.exists():
    pp = pd.read_csv(per_pb_csv)
    save_json("10_per_pb_f1", {"records": pp.to_dict(orient="records")})

# Fig 17/18: validation primary
vp_csv = TAB / "validation_primary_summary.csv"
if vp_csv.exists():
    vp = pd.read_csv(vp_csv)
    save_json("17_18_validation_primary", {"summary": vp.to_dict(orient="records")})

# Fig 19/20: success formula + rank
sf_csv = TAB / "success_formula_summary.csv"
if sf_csv.exists():
    sf = pd.read_csv(sf_csv)
    save_json("19_success_formula", {"summary": sf.to_dict(orient="records")})
rs_csv = TAB / "rank_score_summary.csv"
if rs_csv.exists():
    rs = pd.read_csv(rs_csv)
    save_json("20_rank_score", {"summary": rs.to_dict(orient="records")})

print("\n[done]")
