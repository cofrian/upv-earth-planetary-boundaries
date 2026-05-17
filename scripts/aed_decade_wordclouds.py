"""
AED por decadas + wordclouds individuales por PB.

Genera:
  38_decade_pb_trends.png      lineas de publicacion destacadas por decada
  39_wordclouds_individual/    9 wordclouds individuales (uno por PB)
  39_wordclouds_grid.png       grid 3x3 de los 9 wordclouds para la memoria

JSONs paralelos en data_json/.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
ASSIGN = ROOT / "data/corpus/pb_assignments_top3.csv"
AED = ROOT / "docs/eda/aed"
FIG = AED / "figures"
JSON_DIR = AED / "data_json"
WC_DIR = FIG / "39_wordclouds_individual"
WC_DIR.mkdir(parents=True, exist_ok=True)

PB_CODES = [f"PB{i}" for i in range(1, 10)]
PB_NAMES = {
    "PB1": "Climate Change", "PB2": "Ocean Acidification",
    "PB3": "Stratospheric Ozone", "PB4": "Biogeochemical Flows",
    "PB5": "Freshwater Use", "PB6": "Land-System Change",
    "PB7": "Biosphere Integrity", "PB8": "Novel Entities",
    "PB9": "Aerosol Loading",
}
PB_COLORS = {
    "PB1": "#1F4E79", "PB2": "#3F7CAC", "PB3": "#6BAED6", "PB9": "#9ECAE1",
    "PB5": "#2E7D32", "PB6": "#558B2F", "PB7": "#81C784",
    "PB4": "#D26F3D", "PB8": "#B53A1E",
}
PB_CMAP = {
    "PB1": "Blues", "PB2": "PuBu", "PB3": "BuPu", "PB9": "GnBu",
    "PB5": "Greens", "PB6": "YlGn", "PB7": "BuGn",
    "PB4": "Oranges", "PB8": "Reds",
}

mpl.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 10.5,
    "axes.titlesize": 12.5, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "figure.facecolor": "white",
})
SAVE_KW = dict(dpi=300, bbox_inches="tight", facecolor="white")


def save_fig(fig, name):
    fig.savefig(FIG / f"{name}.png", **SAVE_KW)
    fig.savefig(FIG / f"{name}.pdf", **SAVE_KW)
    plt.close(fig)
    print(f"  -> {(FIG/f'{name}.png').relative_to(ROOT)}")


def save_json(name, data):
    (JSON_DIR / f"{name}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=float))


STOPWORDS = set("""
the of and in to a is for on with by are this that we from as it our be at can
have has paper study research analysis using used results show shows two also
which not but their there these those an its more most than such over per into
been when where one new use using based both was were will would during after
before each other another between within among through about they them then thus
however therefore while although since because high low large small different
similar same significant significantly study studies found observed obtained
provide provided present presented develop developed method methods approach
result effect effects increase decrease change changes data model models analysis
system systems area areas case cases value values year years time times level
levels number rate ratio total mean average key word words abstract introduction
conclusion section figure table creative commons attribution copyright license
licensed published publication publications copernicus european geosciences union
behalf terms access open competing interests author authors article journal
elsevier wiley springer mdpi reserved rights doi http https www available online
received accepted january february march april may june july august september
october november december university press editor review reviewed corresponding
email distributed distribution reproduction medium original source credited
permits unrestricted provided properly cited noncommercial distribute role design
collection decision publish preparation manuscript funding funders sponsors
frontiers specialty submitted edited reviewed editorial section frontiersin
volume issue pages chapter book proceedings conference workshop symposium
""".split())
_BROKEN = {"signi", "cant", "cantly", "speci", "ned", "ndings", "rst",
           "uence", "ux", "uid", "elds", "cation", "ed"}


def tokenize(text):
    if pd.isna(text): return []
    text = str(text).lower()
    for a, b in [("signi cant", "significant"), ("acidi cation", "acidification"),
                 ("classi cation", "classification"), ("identi ed", "identified"),
                 ("modi ed", "modified"), ("speci c", "specific")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z\s-]", " ", text)
    out = []
    for t in text.split():
        t = t.strip("-")
        if 4 <= len(t) <= 24 and t not in STOPWORDS and t not in _BROKEN:
            out.append(t)
    return out


# ---------------------------------------------------------------------------
# Load + join
# ---------------------------------------------------------------------------
print("[load] corpus + pb assignments")
co = pd.read_csv(CORPUS, low_memory=False)
co["year"] = pd.to_numeric(co["year"], errors="coerce")
asg = pd.read_csv(ASSIGN, low_memory=False)
df = asg[["doc_id", "pb1", "year"]].merge(
    co[["doc_id", "clean_abstract", "abstract_norm"]], on="doc_id", how="left")
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df[df["pb1"].isin(PB_CODES)]
df["text"] = df["clean_abstract"].fillna(df["abstract_norm"].fillna(""))
print(f"  {len(df):,} papers con PB1 asignado")


# ---------------------------------------------------------------------------
# decade PB trends
# ---------------------------------------------------------------------------
print("\n[fig 38] decade PB trends")

dy = df.dropna(subset=["year"]).copy()
dy["year"] = dy["year"].astype(int)
dy = dy[(dy["year"] >= 1990) & (dy["year"] <= 2024)]

decades = [("1990-1999", 1990, 1999), ("2000-2009", 2000, 2009),
           ("2010-2019", 2010, 2019), ("2020-2024", 2020, 2024)]

decade_data = {}
for lab, y1, y2 in decades:
    sub = dy[(dy["year"] >= y1) & (dy["year"] <= y2)]
    counts = sub["pb1"].value_counts().reindex(PB_CODES, fill_value=0)
    pct = (counts / counts.sum() * 100).round(1) if counts.sum() else counts
    decade_data[lab] = {"n_papers": int(len(sub)),
                        "counts": {c: int(counts[c]) for c in PB_CODES},
                        "pct": {c: float(pct[c]) for c in PB_CODES}}

fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(2, 4, hspace=0.5, wspace=0.35, height_ratios=[1, 1])

# top row: 4 mini barplots, one per decade (% share by PB)
for i, (lab, y1, y2) in enumerate(decades):
    ax = fig.add_subplot(gs[0, i])
    pct = pd.Series(decade_data[lab]["pct"])
    order = pct.sort_values(ascending=True)
    ax.barh(range(len(order)), order.values,
            color=[PB_COLORS[c] for c in order.index], edgecolor="white")
    for j, (c, v) in enumerate(order.items()):
        if v > 0:
            ax.text(v + 1, j, f"{v:.0f}%", va="center", fontsize=7.5, color="#444")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order.index, fontsize=8)
    ax.set_xlim(0, max(pct.values) * 1.25 if pct.max() else 1)
    ax.set_title(f"{lab}\nN={decade_data[lab]['n_papers']:,}",
                 fontsize=10, weight="bold", color="#1F4E79")
    ax.set_xlabel("% papers", fontsize=8)
    ax.tick_params(labelsize=8)

# bottom: bump chart - rank of each PB across decades
ax = fig.add_subplot(gs[1, :])
rank_by_decade = {}
for lab in [d[0] for d in decades]:
    pct = pd.Series(decade_data[lab]["pct"])
    ranks = pct.rank(ascending=False, method="first")
    rank_by_decade[lab] = ranks

xs = list(range(len(decades)))
for c in PB_CODES:
    ys = [rank_by_decade[d[0]][c] for d in decades]
    ax.plot(xs, ys, "-o", color=PB_COLORS[c], lw=2.2, markersize=9,
            markeredgecolor="white", markeredgewidth=1.5)
    ax.text(-0.12, ys[0], f"{c}", ha="right", va="center",
            fontsize=9, color=PB_COLORS[c], weight="bold")
    ax.text(len(decades)-1+0.12, ys[-1], f"{c} {PB_NAMES[c]}", ha="left",
            va="center", fontsize=9, color=PB_COLORS[c], weight="bold")
ax.set_xticks(xs)
ax.set_xticklabels([d[0] for d in decades], fontsize=10)
ax.set_yticks(range(1, 10))
ax.set_ylabel("Ranking (1 = línea más destacada)")
ax.invert_yaxis()
ax.set_xlim(-1.2, len(decades) + 1.2)
ax.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.6)
ax.set_axisbelow(True)
ax.set_title("Bump chart: evolución del ranking de cada línea PB por década",
             loc="left", weight="bold", fontsize=12)

save_fig(fig, "38_decade_pb_trends")

save_json("38_decade_pb_trends", {
    "decades": decade_data,
    "ranking_by_decade": {lab: {c: int(rank_by_decade[lab][c]) for c in PB_CODES}
                          for lab in [d[0] for d in decades]},
})

# Console: dominant lines per decade
print("\n  Líneas destacadas por década:")
for lab in [d[0] for d in decades]:
    pct = pd.Series(decade_data[lab]["pct"]).sort_values(ascending=False)
    top3 = ", ".join(f"{c} ({pct[c]:.0f}%)" for c in pct.index[:3])
    print(f"    {lab}: {top3}")


# ---------------------------------------------------------------------------
# individual wordclouds per PB (full corpus)
# ---------------------------------------------------------------------------
print("\n[fig 39] wordclouds individuales por PB")

try:
    from wordcloud import WordCloud
    has_wc = True
except ImportError:
    has_wc = False
    print("  [warn] wordcloud no instalado")

wc_terms = {}
if has_wc:
    for c in PB_CODES:
        sub = df[df["pb1"] == c]
        n = len(sub)
        sample = sub["text"].sample(min(2500, n), random_state=7) if n else []
        toks = []
        for t in sample:
            toks.extend(tokenize(t))
        freq = Counter(toks)
        # quitar el propio nombre del PB para que el wordcloud sea informativo
        wc_terms[c] = [{"term": t, "count": ct} for t, ct in freq.most_common(40)]
        if not freq:
            continue
        wc = WordCloud(width=900, height=600, background_color="white",
                       colormap=PB_CMAP[c], max_words=90, prefer_horizontal=0.92,
                       relative_scaling=0.5).generate_from_frequencies(dict(freq))
        fig, ax = plt.subplots(figsize=(7, 4.6))
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
        ax.set_title(f"{c} - {PB_NAMES[c]}  (N={n:,})",
                     loc="left", fontsize=12, weight="bold", color=PB_COLORS[c])
        fig.savefig(WC_DIR / f"{c.lower()}_wordcloud.png", **SAVE_KW)
        plt.close(fig)
        print(f"  -> {(WC_DIR/f'{c.lower()}_wordcloud.png').relative_to(ROOT)}")

    # Grid 3x3 para la memoria
    fig, axes = plt.subplots(3, 3, figsize=(16, 11))
    for ax, c in zip(axes.flatten(), PB_CODES):
        sub = df[df["pb1"] == c]
        n = len(sub)
        sample = sub["text"].sample(min(2500, n), random_state=7) if n else []
        toks = []
        for t in sample:
            toks.extend(tokenize(t))
        freq = Counter(toks)
        if freq:
            wc = WordCloud(width=700, height=460, background_color="white",
                           colormap=PB_CMAP[c], max_words=70, prefer_horizontal=0.92,
                           relative_scaling=0.5).generate_from_frequencies(dict(freq))
            ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title(f"{c} - {PB_NAMES[c]}  (N={n:,})",
                     loc="left", fontsize=11, weight="bold", color=PB_COLORS[c])
    save_fig(fig, "39_wordclouds_grid")

save_json("39_wordclouds_individual", {
    "per_pb_top_terms": wc_terms,
})


# ---------------------------------------------------------------------------
# Figure 40 - semantic topics (KMeans on TF-IDF of abstracts)
# ---------------------------------------------------------------------------
print("\n[fig 40] topics semanticos (KMeans sobre TF-IDF)")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

sample_n = min(15000, len(df))
sample = df.sample(sample_n, random_state=11).copy()
clean_texts = sample["text"].map(lambda t: " ".join(tokenize(t)))
clean_texts = clean_texts[clean_texts.str.len() > 0]
print(f"  vectorizando {len(clean_texts):,} abstracts")

vec = TfidfVectorizer(max_features=8000, min_df=5, max_df=0.5, ngram_range=(1, 2))
X = vec.fit_transform(clean_texts)
vocab = np.array(vec.get_feature_names_out())

K = 8
km = KMeans(n_clusters=K, random_state=11, n_init=10).fit(X)
labels_km = km.labels_

# top terminos por cluster (centroides TF-IDF)
topics = []
for k in range(K):
    centroid = km.cluster_centers_[k]
    top_idx = np.argsort(-centroid)[:8]
    terms = [vocab[i] for i in top_idx]
    n_k = int((labels_km == k).sum())
    topics.append({"cluster": k, "terms": terms, "n_papers": n_k,
                   "pct": round(n_k / len(clean_texts) * 100, 1)})
topics.sort(key=lambda t: -t["n_papers"])

fig, ax = plt.subplots(figsize=(13, 7.5))
ax.axis("off")
pal = plt.cm.viridis(np.linspace(0.12, 0.88, K))
y = 0.96
row_h = 0.96 / K
for rank, t in enumerate(topics):
    col = pal[rank]
    # barra de peso
    bar_w = t["pct"] / max(x["pct"] for x in topics) * 0.62
    ax.add_patch(plt.Rectangle((0.30, y - row_h*0.62), bar_w, row_h*0.30,
                                facecolor=col, edgecolor="none",
                                transform=ax.transAxes))
    ax.text(0.0, y - row_h*0.30, f"TEMA {rank+1}",
            fontsize=9, color="#888", weight="bold", transform=ax.transAxes)
    ax.text(0.0, y - row_h*0.62, ", ".join(t["terms"][:5]),
            fontsize=11, color="#222", weight="bold", transform=ax.transAxes)
    ax.text(0.94, y - row_h*0.30, f"{t['n_papers']:,} papers",
            fontsize=9.5, color="#444", ha="right", transform=ax.transAxes)
    ax.text(0.94, y - row_h*0.62, f"{t['pct']:.1f}%",
            fontsize=10, color=col, weight="bold", ha="right",
            transform=ax.transAxes)
    y -= row_h
save_fig(fig, "40_semantic_topics")

save_json("40_semantic_topics", {
    "method": "KMeans (k=8) sobre TF-IDF (1-2 gramas) de los abstracts",
    "n_papers_clustered": int(len(clean_texts)),
    "topics": topics,
})
print("  temas detectados:")
for rank, t in enumerate(topics):
    print(f"    Tema {rank+1} ({t['pct']:.1f}%): {', '.join(t['terms'][:5])}")


# ---------------------------------------------------------------------------
# Figure 41 - stacked area: produccion anual apilada por PB
# ---------------------------------------------------------------------------
print("\n[fig 41] stacked area produccion anual por PB")

sa = dy.copy()  # ya tiene year int 1990-2024
yr_pb = (sa.groupby(["year", "pb1"]).size().unstack(fill_value=0)
         .reindex(columns=PB_CODES, fill_value=0))
years = yr_pb.index.values

fig, ax = plt.subplots(figsize=(14, 6.5))
ys = [yr_pb[c].values for c in PB_CODES]
ax.stackplot(years, ys, labels=[f"{c} {PB_NAMES[c]}" for c in PB_CODES],
             colors=[PB_COLORS[c] for c in PB_CODES],
             edgecolor="white", linewidth=0.35)
ax.set_xlabel("Año"); ax.set_ylabel("Publicaciones por año (PB principal)")
ax.set_xlim(years.min(), years.max())
ax.legend(loc="upper left", fontsize=8.5, ncol=3)
ax.grid(True, axis="y", linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.6)
ax.set_axisbelow(True)
# anotar pico y caida
peak_y = int(yr_pb.sum(axis=1).idxmax())
peak_v = int(yr_pb.sum(axis=1).max())
ax.annotate(f"pico {peak_y}: {peak_v:,}", xy=(peak_y, peak_v),
            xytext=(peak_y-13, peak_v*0.92),
            arrowprops=dict(arrowstyle="->", color="#666"),
            fontsize=10, color="#333", weight="bold")
save_fig(fig, "41_stacked_area_pb")

save_json("41_stacked_area_pb", {
    "years": years.tolist(),
    "series": {c: yr_pb[c].astype(int).tolist() for c in PB_CODES},
    "peak_year": peak_y, "peak_value": peak_v,
})

print("\n[done]")
