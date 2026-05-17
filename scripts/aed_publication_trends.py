"""
AED de tendencias de publicacion UPV: distribuciones, top journals, palabras emergentes.

Genera:
  30_publication_trends.png       crecimiento absoluto + tasa anual + acumulada
  31_top_journals.png             top 25 journals
  32_length_distribution.png      longitud abstract: hist + boxplot por anyo
  33_top_unigrams_bigrams.png     unigramas y bigramas top
  34_emerging_terms.png           keywords con mayor crecimiento reciente
  35_wordcloud_global.png         wordcloud del corpus completo
  36_top_sources.png              fuentes y completitud por anyo
  37_authorship_collaboration.png n autores por paper, distribucion

JSONs y CSVs paralelos en data_json/ y tables/.
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
from matplotlib.patches import Rectangle
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/master_corpus_mixto_clean_enriched.csv"
AED = ROOT / "docs/eda/aed"
FIG = AED / "figures"
TAB = AED / "tables"
JSON_DIR = AED / "data_json"

mpl.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 10.5,
    "axes.titlesize": 12.5, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#444", "xtick.color": "#444", "ytick.color": "#444",
    "legend.frameon": False, "figure.facecolor": "white",
})

ACCENT = "#1F4E79"
ACCENT2 = "#3F7CAC"
ACCENT3 = "#9ECAE1"
GREEN = "#2e8b57"
RED = "#d63a3a"
ORANGE = "#D26F3D"

SAVE_KW = dict(dpi=300, bbox_inches="tight", facecolor="white")


def save_fig(fig, name):
    fig.savefig(FIG / f"{name}.png", **SAVE_KW)
    fig.savefig(FIG / f"{name}.pdf", **SAVE_KW)
    plt.close(fig)
    print(f"  -> {(FIG/f'{name}.png').relative_to(ROOT)}")


def save_json(name, data):
    p = JSON_DIR / f"{name}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=float))


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
print("[load] corpus")
co = pd.read_csv(CORPUS, low_memory=False)
co["year"] = pd.to_numeric(co["year"], errors="coerce")
co = co[(co["year"].isna()) | ((co["year"] >= 1980) & (co["year"] <= 2025))]
n_total = len(co)
print(f"  {n_total:,} papers")


# ---------------------------------------------------------------------------
# publication trends (absolute + growth rate + cumulative)
# ---------------------------------------------------------------------------
print("\n[fig 30] publication trends")

yc = co.dropna(subset=["year"]).copy()
yc["year"] = yc["year"].astype(int)
yc = yc[(yc["year"] >= 1990) & (yc["year"] <= 2024)]
ts = yc.groupby("year").size()

# growth rate YoY
gr = (ts.pct_change() * 100).fillna(0)
# cumulative
cum = ts.cumsum()

fig = plt.figure(figsize=(15, 9))
gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.3)

# (a) absolute volume
ax = fig.add_subplot(gs[0, 0])
ax.fill_between(ts.index, ts.values, color=ACCENT, alpha=0.18)
ax.plot(ts.index, ts.values, color=ACCENT, lw=2.2)
peak_y, peak_v = ts.idxmax(), ts.max()
ax.annotate(f"pico {peak_y}: {peak_v:,}", xy=(peak_y, peak_v),
            xytext=(peak_y-12, peak_v*0.92),
            arrowprops=dict(arrowstyle="->", color="#666"),
            fontsize=10, color="#333", weight="bold")
ax.set_xlabel("Año"); ax.set_ylabel("Publicaciones")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("a. Volumen anual de publicaciones UPV", loc="left")

# (b) growth rate YoY
ax = fig.add_subplot(gs[0, 1])
colors = [GREEN if v >= 0 else RED for v in gr.values]
ax.bar(gr.index, gr.values, color=colors, edgecolor="white", linewidth=0.4)
ax.axhline(0, color="#444", lw=0.6)
ax.set_xlabel("Año"); ax.set_ylabel("Δ % año a año")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("b. Tasa de crecimiento anual (YoY)", loc="left")

# (c) cumulative
ax = fig.add_subplot(gs[1, 0])
ax.fill_between(cum.index, cum.values, color=ACCENT2, alpha=0.3)
ax.plot(cum.index, cum.values, color=ACCENT, lw=2.2)
ax.set_xlabel("Año"); ax.set_ylabel("Publicaciones acumuladas")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("c. Producción acumulada", loc="left")
# milestones
for milestone_year in [2000, 2010, 2015, 2020]:
    if milestone_year in cum.index:
        ax.axvline(milestone_year, color="#999", lw=0.5, linestyle="--", alpha=0.6)
        ax.text(milestone_year, cum.max()*0.05, str(milestone_year),
                ha="center", fontsize=8, color="#666")

# (d) period summary
ax = fig.add_subplot(gs[1, 1])
periods = [("1990-1999", 1990, 1999), ("2000-2009", 2000, 2009),
           ("2010-2019", 2010, 2019), ("2020-2024", 2020, 2024)]
labels, totals, means_per_year = [], [], []
for lab, y1, y2 in periods:
    sub = ts[(ts.index >= y1) & (ts.index <= y2)]
    labels.append(lab); totals.append(int(sub.sum())); means_per_year.append(sub.mean())
xs = np.arange(len(labels))
b = ax.bar(xs, totals, color=ACCENT, edgecolor="white", alpha=0.85)
for bar, t, m in zip(b, totals, means_per_year):
    ax.text(bar.get_x()+bar.get_width()/2, t + max(totals)*0.01,
            f"{t:,}\n({m:.0f}/año)", ha="center", fontsize=9, color="#333")
ax.set_xticks(xs); ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_ylabel("Publicaciones por periodo")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
ax.set_title("d. Producción por décadas (total / promedio anual)", loc="left")

save_fig(fig, "30_publication_trends")

save_json("30_publication_trends", {
    "n_with_year": int(len(yc)),
    "year_min": int(ts.index.min()), "year_max": int(ts.index.max()),
    "peak_year": int(peak_y), "peak_value": int(peak_v),
    "yearly": {int(y): int(v) for y, v in ts.items()},
    "growth_yoy_pct": {int(y): float(v) for y, v in gr.items()},
    "cumulative": {int(y): int(v) for y, v in cum.items()},
    "periods": [{"period": l, "total": t, "mean_per_year": round(m, 1)}
                for l, t, m in zip(labels, totals, means_per_year)],
})


# ---------------------------------------------------------------------------
# top journals
# ---------------------------------------------------------------------------
print("\n[fig 31] top journals")
jr = co["journal"].dropna().astype(str).str.strip()
jr = jr[jr != ""]
# filtrar basura de extraccion PDF
_JUNK = re.compile(r"^(untitled|publication date|no title|nan|none|n/?a|"
                   r"\d+|.{0,3}|microsoft word.*|.*\.docx?|.*\.pdf)$", re.IGNORECASE)
jr_clean = jr[~jr.str.match(_JUNK)]
jr_clean = jr_clean[jr_clean.str.len().between(4, 80)]
jc = jr_clean.value_counts().head(25)

fig, ax = plt.subplots(figsize=(11, 9))
order = jc.iloc[::-1]
colors_g = plt.cm.viridis(np.linspace(0.15, 0.85, len(order)))
bars = ax.barh(range(len(order)), order.values, color=colors_g,
               edgecolor="white", linewidth=0.4)
for i, (name, v) in enumerate(zip(order.index, order.values)):
    ax.text(v + max(order.values)*0.005, i, f"{v:,}",
            va="center", fontsize=9, color="#333")
ax.set_yticks(range(len(order)))
ax.set_yticklabels([n[:55] for n in order.index], fontsize=9)
ax.set_xlabel("# papers UPV")
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)
save_fig(fig, "31_top_journals")

save_json("31_top_journals", {
    "n_papers_with_journal_clean": int(len(jr_clean)),
    "top_journals": [{"journal": k, "count": int(v)} for k, v in jc.items()],
})

# ---------------------------------------------------------------------------
# length distribution
# ---------------------------------------------------------------------------
print("\n[fig 32] length distribution")
lens = co["abstract_norm_len"].dropna()
lens = lens[(lens > 0) & (lens < 6000)]

fig = plt.figure(figsize=(14, 6))
gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=0.25)

# Histogram
ax = fig.add_subplot(gs[0])
ax.hist(lens, bins=60, color=ACCENT2, edgecolor="white", linewidth=0.4)
ax.axvline(lens.median(), color=RED, lw=1.4, linestyle="--",
           label=f"mediana = {int(lens.median()):,}")
ax.axvline(lens.mean(), color=ORANGE, lw=1.4, linestyle="--",
           label=f"media = {int(lens.mean()):,}")
ax.legend(loc="upper right", fontsize=10)
ax.set_xlabel("Longitud abstract (chars)"); ax.set_ylabel("# papers")
ax.set_title("a. Distribución de longitud", loc="left")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

# Box plot by 5-year buckets
ax = fig.add_subplot(gs[1])
df_l = co.dropna(subset=["year", "abstract_norm_len"]).copy()
df_l["year"] = df_l["year"].astype(int)
df_l = df_l[(df_l["year"] >= 1995) & (df_l["year"] <= 2024)]
df_l["bucket"] = pd.cut(df_l["year"],
    bins=[1994, 2000, 2005, 2010, 2015, 2020, 2025],
    labels=["1995-00", "01-05", "06-10", "11-15", "16-20", "21-24"])
data_b = [df_l[df_l["bucket"]==b]["abstract_norm_len"].values for b in df_l["bucket"].cat.categories]
bp = ax.boxplot(data_b, labels=df_l["bucket"].cat.categories, showfliers=False,
                patch_artist=True, widths=0.6)
for patch in bp["boxes"]:
    patch.set_facecolor(ACCENT3); patch.set_edgecolor(ACCENT)
for m in bp["medians"]:
    m.set_color(RED); m.set_lw(1.5)
ax.set_xlabel("Periodo"); ax.set_ylabel("longitud (chars)")
ax.set_title("b. Evolución de la longitud por periodo", loc="left")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

save_fig(fig, "32_length_distribution")

stats = lens.describe().to_dict()
save_json("32_length_distribution", {
    "n_with_length": int(len(lens)),
    "mean": float(stats["mean"]), "median": float(stats["50%"]),
    "p10": float(np.percentile(lens, 10)), "p25": float(stats["25%"]),
    "p75": float(stats["75%"]), "p90": float(np.percentile(lens, 90)),
    "max": float(stats["max"]),
})

# ---------------------------------------------------------------------------
# top unigrams + bigrams + trigrams
# ---------------------------------------------------------------------------
print("\n[fig 33] top n-grams")

STOPWORDS = set("""
the of and in to a is for on with by are this that we from as it our be at can
have has paper study research analysis using used results show shows two also
which not but their there these those an its more most than such over per into
been when where also one new used use using based both was were will would
during after before each other another between within among through about
these those they them then thus however therefore while although since because
high low large small different similar same significant significantly study studies
found observed obtained provide provided present presented develop developed
method methods approach result effect effects increase decrease change changes
data model models analysis system systems area areas case cases value values
year years time times level levels number rate ratio total mean average
key word words abstract introduction conclusion section figure table
creative commons attribution copyright license licensed published publication
publications copernicus european geosciences union behalf terms access open
competing interests author authors article journal elsevier wiley springer
mdpi reserved rights doi http https www available online received accepted
january february march april may june july august september october november
december university press editor review reviewed corresponding email
distributed distribution reproduction medium original source credited permits
unrestricted provided properly cited noncommercial use distribute attribution
resale republication permitted without written consent publisher role design
collection decision publish preparation manuscript funding funders sponsors
""".split())

# Fragmentos rotos por ligaduras de extraccion PDF (fi, fl perdidas)
_BROKEN = {"signi", "cant", "cantly", "speci", "ned", "ndings", "rst",
           "ndia", "ned", "uence", "ux", "uid", "elds", "ow", "nds"}

def tokenize(text):
    if pd.isna(text): return []
    text = str(text).lower()
    # reparar ligaduras rotas comunes
    text = text.replace("signi cant", "significant").replace("signi cantly", "significantly")
    text = text.replace("acidi cation", "acidification").replace("classi cation", "classification")
    text = text.replace("identi ed", "identified").replace("modi ed", "modified")
    text = re.sub(r"[^a-z\s-]", " ", text)
    toks = []
    for t in text.split():
        t = t.strip("-")
        if len(t) < 4 or len(t) > 24:
            continue
        if t in STOPWORDS or t in _BROKEN:
            continue
        toks.append(t)
    return toks

texts = co["clean_abstract"].fillna(co["abstract_norm"].fillna("")).astype(str)
print("  tokenizing...")
all_toks = []
for t in texts.sample(min(20000, len(texts)), random_state=1):
    all_toks.append(tokenize(t))
print(f"  done. {sum(len(t) for t in all_toks):,} tokens")

# unigrams
uc = Counter(tok for sent in all_toks for tok in sent)
# bigrams
bc = Counter()
for sent in all_toks:
    for i in range(len(sent)-1):
        bc[(sent[i], sent[i+1])] += 1
# trigrams
tc = Counter()
for sent in all_toks:
    for i in range(len(sent)-2):
        tc[(sent[i], sent[i+1], sent[i+2])] += 1

top_uni = uc.most_common(25)
top_bi = bc.most_common(25)
top_tri = tc.most_common(15)

fig, axes = plt.subplots(1, 3, figsize=(18, 8), gridspec_kw=dict(wspace=0.5))

# unigrams
ax = axes[0]
labels = [t for t, _ in top_uni][::-1]
vals = [c for _, c in top_uni][::-1]
ax.barh(range(len(labels)), vals,
        color=plt.cm.Blues(np.linspace(0.4, 0.9, len(labels))), edgecolor="white")
for i, v in enumerate(vals):
    ax.text(v + max(vals)*0.01, i, f"{v:,}", va="center", fontsize=8)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("frecuencia")
ax.set_title("a. Top 25 unigramas", loc="left", weight="bold")

# bigrams
ax = axes[1]
labels = [" ".join(t) for t, _ in top_bi][::-1]
vals = [c for _, c in top_bi][::-1]
ax.barh(range(len(labels)), vals,
        color=plt.cm.Greens(np.linspace(0.4, 0.9, len(labels))), edgecolor="white")
for i, v in enumerate(vals):
    ax.text(v + max(vals)*0.01, i, f"{v:,}", va="center", fontsize=8)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("frecuencia")
ax.set_title("b. Top 25 bigramas", loc="left", weight="bold")

# trigrams
ax = axes[2]
labels = [" ".join(t) for t, _ in top_tri][::-1]
vals = [c for _, c in top_tri][::-1]
ax.barh(range(len(labels)), vals,
        color=plt.cm.Oranges(np.linspace(0.4, 0.9, len(labels))), edgecolor="white")
for i, v in enumerate(vals):
    ax.text(v + max(vals)*0.01, i, f"{v:,}", va="center", fontsize=8)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8.5)
ax.set_xlabel("frecuencia")
ax.set_title("c. Top 15 trigramas", loc="left", weight="bold")

save_fig(fig, "33_top_ngrams")

save_json("33_top_ngrams", {
    "unigrams": [{"term": t, "count": c} for t, c in top_uni],
    "bigrams": [{"term": " ".join(t), "count": c} for t, c in top_bi],
    "trigrams": [{"term": " ".join(t), "count": c} for t, c in top_tri],
})

# ---------------------------------------------------------------------------
# emerging terms (growth in recent period)
# ---------------------------------------------------------------------------
print("\n[fig 34] emerging terms")

# tokenize por dos periodos: historico (<=2015) y reciente (>=2020)
yc_full = co.dropna(subset=["year"]).copy()
yc_full["year"] = yc_full["year"].astype(int)

hist_texts = yc_full[(yc_full["year"] <= 2015)]["clean_abstract"].fillna("").astype(str)
rec_texts = yc_full[(yc_full["year"] >= 2020)]["clean_abstract"].fillna("").astype(str)
print(f"  hist papers: {len(hist_texts):,} | rec papers: {len(rec_texts):,}")

def count_tokens(texts):
    c = Counter()
    for t in texts:
        for tok in tokenize(t):
            c[tok] += 1
    return c

n_hist_sample = min(8000, len(hist_texts))
n_rec_sample = min(8000, len(rec_texts))
ch = count_tokens(hist_texts.sample(n_hist_sample, random_state=2))
cr = count_tokens(rec_texts.sample(n_rec_sample, random_state=2))

# normalizar por tokens totales
total_h = sum(ch.values()); total_r = sum(cr.values())
candidates = set([t for t, c in ch.items() if c >= 30]) | set([t for t, c in cr.items() if c >= 30])
rows = []
for t in candidates:
    fh = ch.get(t, 0) / total_h
    fr = cr.get(t, 0) / total_r
    if fh < 1e-6 and fr < 1e-6: continue
    log_growth = np.log((fr + 1e-7) / (fh + 1e-7))
    rows.append({"term": t, "freq_historic": fh, "freq_recent": fr,
                 "count_hist": ch.get(t, 0), "count_rec": cr.get(t, 0),
                 "log_growth": log_growth})
emrg = pd.DataFrame(rows).sort_values("log_growth", ascending=False)
emerging_top = emrg.head(20)
declining_top = emrg.tail(15).iloc[::-1]

fig, axes = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw=dict(wspace=0.35))

ax = axes[0]
y = range(len(emerging_top))
ax.barh(y, emerging_top["log_growth"].values,
        color=GREEN, edgecolor="white", alpha=0.85)
for i, (term, lg, ch_, cr_) in enumerate(zip(emerging_top["term"],
                                              emerging_top["log_growth"],
                                              emerging_top["count_hist"],
                                              emerging_top["count_rec"])):
    ax.text(lg + 0.05, i, f"{term}  ({int(ch_)}→{int(cr_)})",
            va="center", fontsize=9, color="#333")
ax.set_yticks([]); ax.set_xlabel("log-growth (frecuencia reciente / histórica)")
ax.set_title("a. Top 20 keywords emergentes (≤2015 → ≥2020)",
             loc="left", weight="bold")
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

ax = axes[1]
y = range(len(declining_top))
ax.barh(y, declining_top["log_growth"].values,
        color=RED, edgecolor="white", alpha=0.85)
for i, (term, lg, ch_, cr_) in enumerate(zip(declining_top["term"],
                                              declining_top["log_growth"],
                                              declining_top["count_hist"],
                                              declining_top["count_rec"])):
    ax.text(lg - 0.05, i, f"({int(ch_)}→{int(cr_)})  {term}",
            va="center", ha="right", fontsize=9, color="#333")
ax.set_yticks([]); ax.set_xlabel("log-growth (negativo = declina)")
ax.set_title("b. Top 15 keywords en declive", loc="left", weight="bold")
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

save_fig(fig, "34_emerging_terms")

save_json("34_emerging_terms", {
    "n_historic_sample": n_hist_sample,
    "n_recent_sample": n_rec_sample,
    "emerging_top20": emerging_top.to_dict(orient="records"),
    "declining_top15": declining_top.to_dict(orient="records"),
})


# ---------------------------------------------------------------------------
# wordcloud (matplotlib alternative if wordcloud installed)
# ---------------------------------------------------------------------------
print("\n[fig 35] wordcloud")
try:
    from wordcloud import WordCloud
    text = " ".join(t for sent in all_toks for t in sent)
    wc = WordCloud(width=1600, height=800, background_color="white",
                   colormap="viridis", max_words=180, prefer_horizontal=0.95,
                   relative_scaling=0.5).generate(text)
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    save_fig(fig, "35_wordcloud_global")
except ImportError:
    print("  [warn] wordcloud no instalado, generando fallback con texto")
    # Fallback: top-30 words as a bubble-ish layout
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    np.random.seed(3)
    top30 = uc.most_common(30)
    max_c = top30[0][1]
    for i, (w, c) in enumerate(top30):
        x = (i * 17) % 90 + np.random.uniform(2, 8)
        y = (i // 5) * 8 + np.random.uniform(2, 5)
        sz = 8 + (c / max_c) * 36
        ax.text(x, y, w, fontsize=sz, color=plt.cm.viridis(c / max_c),
                weight="bold", alpha=0.9)
    save_fig(fig, "35_wordcloud_global")


# ---------------------------------------------------------------------------
# sources + metadata completeness over time
# ---------------------------------------------------------------------------
print("\n[fig 36] sources + completeness over time")

src = co["source"].fillna("unknown").value_counts().head(6)
df_c = co.dropna(subset=["year"]).copy()
df_c["year"] = df_c["year"].astype(int)
df_c = df_c[(df_c["year"] >= 2000) & (df_c["year"] <= 2024)]
# completitud por año
metrics = {}
for col in ["doi", "journal", "keywords", "authors"]:
    metrics[col] = df_c.groupby("year").apply(lambda g: g[col].notna().mean() * 100)

fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw=dict(wspace=0.3))
# sources
ax = axes[0]
colors_s = plt.cm.Blues(np.linspace(0.45, 0.85, len(src)))
ax.barh(src.index[::-1], src.values[::-1], color=colors_s[::-1], edgecolor="white")
for i, v in enumerate(src.values[::-1]):
    ax.text(v + max(src.values)*0.005, i, f"{v:,}", va="center", fontsize=9.5, color="#333")
ax.set_xlabel("# papers")
ax.set_title("a. Fuentes del corpus", loc="left", weight="bold")
ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

# completeness over time
ax = axes[1]
for col, color in zip(["doi", "journal", "keywords", "authors"],
                      [ACCENT, GREEN, ORANGE, "#9b59b6"]):
    ax.plot(metrics[col].index, metrics[col].values, "-o", lw=1.8, ms=3,
            color=color, label=col)
ax.set_xlabel("Año"); ax.set_ylabel("% papers con campo informado")
ax.set_ylim(0, 105)
ax.legend(loc="lower right", fontsize=9.5)
ax.set_title("b. Completitud de metadata por año", loc="left", weight="bold")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

save_fig(fig, "36_sources_completeness")

save_json("36_sources_completeness", {
    "sources": {k: int(v) for k, v in src.items()},
    "completeness_yearly": {col: {int(y): round(float(v), 2)
                                   for y, v in metrics[col].items()}
                            for col in metrics},
})

# ---------------------------------------------------------------------------
# authorship / collaboration
# ---------------------------------------------------------------------------
print("\n[fig 37] authorship")
au = co["authors"].dropna().astype(str)
# count authors (split by ; or , common patterns)
def count_authors(s):
    if not s: return 0
    parts = re.split(r"[;|]", s)
    if len(parts) == 1:
        parts = re.split(r",\s+(?=[A-Z])", s)  # comma followed by capitalized name
    parts = [p.strip() for p in parts if p.strip()]
    return len(parts)

co_au = co.copy()
co_au["n_authors"] = co_au["authors"].fillna("").map(count_authors)
co_au_y = co_au.dropna(subset=["year"]).copy()
co_au_y["year"] = co_au_y["year"].astype(int)
co_au_y = co_au_y[(co_au_y["year"] >= 1995) & (co_au_y["year"] <= 2024)]

dist = co_au["n_authors"].value_counts().sort_index()
dist_g = pd.cut(co_au["n_authors"], bins=[-1, 0, 1, 2, 3, 5, 10, 50, 1000],
                labels=["0 (NA)", "1", "2", "3", "4-5", "6-10", "11-50", "50+"])
dist_g = dist_g.value_counts().reindex(["0 (NA)", "1", "2", "3", "4-5", "6-10", "11-50", "50+"])

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw=dict(wspace=0.3))

ax = axes[0]
ax.bar(range(len(dist_g)), dist_g.values, color=ACCENT2, edgecolor="white")
for i, v in enumerate(dist_g.values):
    if v > 0:
        ax.text(i, v + max(dist_g.values)*0.01, f"{int(v):,}", ha="center",
                fontsize=9, color="#333", weight="bold")
ax.set_xticks(range(len(dist_g))); ax.set_xticklabels(dist_g.index, rotation=20, ha="right")
ax.set_ylabel("# papers")
ax.set_title("a. Distribución del nº de autores por paper", loc="left", weight="bold")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

ax = axes[1]
mean_y = co_au_y.groupby("year")["n_authors"].mean()
ax.plot(mean_y.index, mean_y.values, "-o", color=ACCENT, lw=2, ms=3)
ax.set_xlabel("Año"); ax.set_ylabel("nº autores promedio")
ax.set_title("b. Evolución del tamaño de equipo (promedio anual)", loc="left", weight="bold")
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#cccccc", alpha=0.7)
ax.set_axisbelow(True)

save_fig(fig, "37_authorship_collaboration")

save_json("37_authorship_collaboration", {
    "mean_authors_overall": float(co_au["n_authors"].replace(0, np.nan).mean()),
    "median_authors_overall": float(co_au["n_authors"].replace(0, np.nan).median()),
    "distribution_groups": {k: int(v) for k, v in dist_g.items()},
    "mean_authors_yearly": {int(y): round(float(v), 2) for y, v in mean_y.items()},
})

print("\n[done]")
