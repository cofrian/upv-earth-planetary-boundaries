import argparse
import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wordcloud import WordCloud

BASE_DIR = Path('.')
CLEAN_CSV = BASE_DIR / 'data/corpus/master_corpus_mixto_1000_clean_enriched.csv'
TRACE_CSV = BASE_DIR / 'data/corpus/master_corpus_mixto_1000_traceability.csv'
OUT_DIR = BASE_DIR / 'docs/eda'

GENERIC_STOPWORDS = {
    'university', 'universities', 'study', 'studies', 'paper', 'papers', 'result',
    'results', 'method', 'methods', 'data', 'analysis', 'research', 'approach',
    'approaches', 'based', 'using', 'used', 'show', 'shows', 'shown', 'find',
    'findings', 'conclusion', 'conclusions', 'model', 'models', 'new', 'one',
    'two', 'three', 'also', 'can', 'may', 'among', 'within', 'without', 'across',
    'however', 'therefore', 'thus', 'article', 'authors', 'et', 'al', 'abstract',
    'introduction', 'keyword', 'keywords', 'work', 'works', 'different', 'high',
    'low', 'significant', 'important', 'potential', 'present', 'future',
    'university', 'paper', 'study', 'results', 'result', 'figure', 'fig', 'table',
    'tables', 'author', 'authors', 'introduction', 'conclusion', 'conclusions',
    'background', 'objective', 'objectives', 'methodology', 'discussion',
    'universitys', 'dataset', 'datasets', 'elsevier', 'springer', 'wiley',
    'www', 'http', 'https', 'doi', 'org', 'com',
}

STOPWORDS = set(ENGLISH_STOP_WORDS) | GENERIC_STOPWORDS

PB_DISPLAY_ORDER = [
    '1 - Climate Change',
    '2 - Ocean Acidification',
    '3 - Stratospheric Ozone Depletion',
    '4 - Biogeochemical Flows',
    '5 - Global Freshwater Use',
    '6 - Land System Change',
    '7 - Biosphere Integrity',
    '8 - Novel Entities',
    '9 - Atmospheric Aerosol Loading',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Genera graficos para memoria M2.')
    parser.add_argument('--clean', type=Path, default=CLEAN_CSV, help='CSV limpio/enriquecido')
    parser.add_argument('--trace', type=Path, default=TRACE_CSV, help='CSV trazabilidad con PB')
    parser.add_argument('--out-dir', type=Path, default=OUT_DIR, help='Directorio de salida')
    parser.add_argument('--top-k', type=int, default=10, help='Top palabras por PB en TF-IDF')
    parser.add_argument('--min-df', type=int, default=3, help='Frecuencia minima de termino para TF-IDF')
    parser.add_argument('--sim-min-df', type=int, default=3, help='Frecuencia minima para similitud por corpus')
    return parser.parse_args()


def normalize_pb(pb_value: str) -> str:
    if pd.isna(pb_value):
        return 'Unknown'
    return str(pb_value).strip()


def slugify_pb(pb_value: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', str(pb_value).lower()).strip('_')
    return clean[:80]


def get_ordered_pb_list(pb_series: pd.Series) -> list[str]:
    ordered_pb = [pb for pb in PB_DISPLAY_ORDER if pb in set(pb_series)]
    missing_pb = [pb for pb in sorted(pb_series.dropna().unique()) if pb not in ordered_pb]
    return ordered_pb + missing_pb


def count_words(text: str) -> int:
    if pd.isna(text):
        return 0
    return len(re.findall(r"[a-zA-ZÀ-ÿ]{2,}", str(text)))


def build_circle_mask(size: int = 1000) -> np.ndarray:
    x, y = np.ogrid[:size, :size]
    center = size / 2
    radius = size * 0.47
    dist = np.sqrt((x - center) ** 2 + (y - center) ** 2)
    mask = np.zeros((size, size), dtype=np.uint8)
    mask[dist > radius] = 255
    return mask


def tokenize_text(text: str) -> list[str]:
    if pd.isna(text):
        return []
    tokens = re.findall(r"[a-zA-Z]{3,}", str(text).lower())
    return [t for t in tokens if t not in STOPWORDS]


def build_doc_tokens(row: pd.Series) -> list[str]:
    pieces = []
    for col in ['clean_abstract', 'keywords', 'top_terms_no_stopwords']:
        if col in row and pd.notna(row[col]):
            pieces.append(str(row[col]))
    merged = ' '.join(pieces)
    return tokenize_text(merged)


def plot_tfidf_by_pb(df: pd.DataFrame, out_dir: Path, top_k: int, min_df: int) -> pd.DataFrame:
    texts = df['clean_abstract'].fillna('')
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words='english',
        token_pattern=r'(?u)\b[a-zA-Z]{3,}\b',
        min_df=min_df,
        max_df=0.85,
    )
    tfidf = vectorizer.fit_transform(texts)
    terms = np.array(vectorizer.get_feature_names_out())

    pb_stats_rows = []
    tfidf_rows = []

    pb_list = get_ordered_pb_list(df['pb_folder'])
    tfidf_dir = out_dir / 'tfidf_por_pb'
    tfidf_dir.mkdir(parents=True, exist_ok=True)

    for pb in pb_list:
        mask = df['pb_folder'] == pb
        idx = np.where(mask.to_numpy())[0]

        if len(idx) == 0:
            continue

        sub_mat = tfidf[idx]
        mean_scores = np.asarray(sub_mat.mean(axis=0)).ravel()

        ranked_idx = np.argsort(mean_scores)[::-1]
        ranked_idx = [j for j in ranked_idx if terms[j] not in GENERIC_STOPWORDS][:top_k]

        top_terms = terms[ranked_idx]
        top_scores = mean_scores[ranked_idx]

        for term, score in zip(top_terms, top_scores):
            tfidf_rows.append({'pb_folder': pb, 'term': term, 'tfidf_mean': float(score)})

        pb_stats_rows.append({'pb_folder': pb, 'n_docs': int(len(idx))})

        fig, ax = plt.subplots(figsize=(8.5, 5.5))
        y_pos = np.arange(len(top_terms))
        ax.barh(y_pos, top_scores, color='#0B5D8C', alpha=0.9)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_terms, fontsize=10)
        ax.invert_yaxis()
        ax.set_title(f"TF-IDF Top {top_k} | {pb} (n={len(idx)})", fontsize=12)
        ax.set_xlabel('TF-IDF medio')
        plt.tight_layout()
        fig.savefig(tfidf_dir / f"{slugify_pb(pb)}_tfidf_top{top_k}.png", dpi=220)
        plt.close(fig)

    tfidf_table = pd.DataFrame(tfidf_rows).sort_values(['pb_folder', 'tfidf_mean'], ascending=[True, False])
    tfidf_table.to_csv(out_dir / 'tfidf_top_terms_por_pb.csv', index=False)

    pb_stats = pd.DataFrame(pb_stats_rows).sort_values('pb_folder')
    pb_stats.to_csv(out_dir / 'pb_doc_counts.csv', index=False)

    return tfidf_table


def plot_text_complexity(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    complexity = df[['doc_id', 'pb_folder', 'clean_abstract']].copy()
    complexity['n_words'] = complexity['clean_abstract'].map(count_words)
    complexity = complexity[complexity['n_words'] > 0]

    pb_order = get_ordered_pb_list(complexity['pb_folder'])

    plt.figure(figsize=(18, 7))
    sns.violinplot(
        data=complexity,
        x='pb_folder',
        y='n_words',
        order=pb_order,
        inner='quartile',
        linewidth=1,
        color='#80B1D3',
        cut=0,
    )
    plt.xticks(rotation=30, ha='right')
    plt.xlabel('Planetary Boundary')
    plt.ylabel('Numero de palabras del abstract limpio')
    plt.title('Distribucion de complejidad textual por PB')
    plt.tight_layout()
    plt.savefig(out_dir / 'complejidad_abstract_por_pb_violin.png', dpi=220)
    plt.close()

    summary = complexity.groupby('pb_folder')['n_words'].agg(['count', 'mean', 'median', 'std', 'min', 'max']).reset_index()
    summary.to_csv(out_dir / 'complejidad_abstract_por_pb_summary.csv', index=False)

    return summary


def plot_wordcloud_by_pb(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    pb_list = get_ordered_pb_list(df['pb_folder'])
    wordcloud_dir = out_dir / 'wordcloud_por_pb'
    wordcloud_dir.mkdir(parents=True, exist_ok=True)

    ncols = 3
    nrows = int(np.ceil(len(pb_list) / ncols))
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(18, 4.8 * nrows), constrained_layout=True)
    axes = np.array(axes).reshape(-1)

    freq_rows = []

    for i, pb in enumerate(pb_list):
        ax = axes[i]
        subset = df[df['pb_folder'] == pb]

        counter = Counter()
        for _, row in subset.iterrows():
            # Conteo unico por documento para evitar que un solo abstract muy largo domine.
            doc_unique_tokens = set(build_doc_tokens(row))
            counter.update(doc_unique_tokens)

        if not counter:
            ax.set_axis_off()
            continue

        for term, count in counter.most_common(80):
            freq_rows.append({'pb_folder': pb, 'term': term, 'doc_frequency': int(count)})

        wc = WordCloud(
            width=1200,
            height=800,
            background_color='white',
            colormap='GnBu',
            max_words=90,
            min_font_size=8,
            contour_width=0,
            mask=build_circle_mask(800),
            collocations=False,
            random_state=42,
            prefer_horizontal=0.85,
        ).generate_from_frequencies(counter)

        fig_pb, ax_pb = plt.subplots(figsize=(8, 6))
        ax_pb.imshow(wc, interpolation='bilinear')
        ax_pb.set_title(f"WordCloud | {pb} (n={len(subset)})", fontsize=12)
        ax_pb.axis('off')
        plt.tight_layout()
        fig_pb.savefig(wordcloud_dir / f"{slugify_pb(pb)}_wordcloud.png", dpi=240, facecolor='white')
        plt.close(fig_pb)

        ax.imshow(wc, interpolation='bilinear')
        ax.set_title(f"{pb} (n={len(subset)})", fontsize=11)
        ax.axis('off')

    for j in range(len(pb_list), len(axes)):
        axes[j].set_axis_off()

    fig.suptitle('WordCloud por PB (clean_abstract + keywords + top_terms_no_stopwords)', fontsize=16, y=1.02)
    fig.savefig(out_dir / 'wordcloud_por_pb_grid.png', dpi=240, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    freq_table = pd.DataFrame(freq_rows).sort_values(['pb_folder', 'doc_frequency'], ascending=[True, False])
    freq_table.to_csv(out_dir / 'wordcloud_por_pb_top_terms.csv', index=False)
    return freq_table


def save_similarity_outputs(sim_df: pd.DataFrame, out_dir: Path, stem: str, title: str) -> pd.DataFrame:
    sim_df.to_csv(out_dir / f'{stem}.csv', index=True)

    plt.figure(figsize=(10.5, 8.5))
    sns.heatmap(sim_df, annot=True, fmt='.2f', cmap='YlGnBu', vmin=0, vmax=1, square=True)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_dir / f'{stem}.png', dpi=220)
    plt.close()

    rows = []
    labels = sim_df.index.tolist()
    for i, pb_i in enumerate(labels):
        for j, pb_j in enumerate(labels):
            if j <= i:
                continue
            rows.append({'pb_a': pb_i, 'pb_b': pb_j, 'similarity': float(sim_df.iloc[i, j])})

    top_pairs = pd.DataFrame(rows).sort_values('similarity', ascending=False)
    top_pairs.to_csv(out_dir / f'{stem}_top_pairs.csv', index=False)
    return top_pairs


def analyze_similarity_by_terms(tfidf_table: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    if tfidf_table.empty:
        return pd.DataFrame()

    weighted = tfidf_table.pivot_table(index='pb_folder', columns='term', values='tfidf_mean', fill_value=0.0)
    pb_order = get_ordered_pb_list(weighted.index.to_series())
    weighted = weighted.reindex(pb_order)

    sim = cosine_similarity(weighted.values)
    sim_df = pd.DataFrame(sim, index=weighted.index, columns=weighted.index)

    return save_similarity_outputs(
        sim_df,
        out_dir,
        stem='similitud_pb_por_terminos_tfidf',
        title='Similitud entre PB por terminos TF-IDF extraidos (coseno)',
    )


def analyze_similarity_by_corpus(df: pd.DataFrame, out_dir: Path, min_df: int = 3) -> pd.DataFrame:
    corpus = df.copy()
    corpus['text_for_similarity'] = (
        corpus['clean_abstract'].fillna('')
        + ' '
        + corpus['keywords'].fillna('')
        + ' '
        + corpus['top_terms_no_stopwords'].fillna('')
    )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words='english',
        token_pattern=r'(?u)\b[a-zA-Z]{3,}\b',
        min_df=min_df,
        max_df=0.85,
    )
    mat = vectorizer.fit_transform(corpus['text_for_similarity'])

    pb_order = get_ordered_pb_list(corpus['pb_folder'])
    centroids = []
    labels = []
    for pb in pb_order:
        idx = np.where((corpus['pb_folder'] == pb).to_numpy())[0]
        if len(idx) == 0:
            continue
        centroid = np.asarray(mat[idx].mean(axis=0)).ravel()
        centroids.append(centroid)
        labels.append(pb)

    if not centroids:
        return pd.DataFrame()

    centroid_mat = np.vstack(centroids)
    sim = cosine_similarity(centroid_mat)
    sim_df = pd.DataFrame(sim, index=labels, columns=labels)

    return save_similarity_outputs(
        sim_df,
        out_dir,
        stem='similitud_pb_por_corpus_completo',
        title='Similitud entre PB por corpus completo (coseno sobre centroides TF-IDF)',
    )


def build_dataset(clean_path: Path, trace_path: Path) -> pd.DataFrame:
    clean = pd.read_csv(clean_path)
    trace = pd.read_csv(trace_path)

    pb_cols = trace[['doc_id', 'pb_folder']].copy()
    pb_cols['pb_folder'] = pb_cols['pb_folder'].map(normalize_pb)

    merged = clean.merge(pb_cols, on='doc_id', how='left')
    merged = merged[merged['clean_abstract'].fillna('').str.len() > 0].copy()
    merged = merged[merged['pb_folder'].notna()]
    merged = merged[merged['pb_folder'] != 'Unknown']

    for optional_col in ['keywords', 'top_terms_no_stopwords']:
        if optional_col not in merged.columns:
            merged[optional_col] = ''

    return merged


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = build_dataset(args.clean, args.trace)

    tfidf_table = plot_tfidf_by_pb(df, args.out_dir, args.top_k, args.min_df)
    complexity_summary = plot_text_complexity(df, args.out_dir)
    wordcloud_table = plot_wordcloud_by_pb(df, args.out_dir)
    sim_terms_pairs = analyze_similarity_by_terms(tfidf_table, args.out_dir)
    sim_corpus_pairs = analyze_similarity_by_corpus(df, args.out_dir, min_df=args.sim_min_df)

    print('Graficos y tablas de memoria M2 generados correctamente.')
    print(f'Filas usadas: {len(df)}')
    print(f'Top TF-IDF guardado en: {args.out_dir / "tfidf_top_terms_por_pb.csv"}')
    print(f'Resumen complejidad guardado en: {args.out_dir / "complejidad_abstract_por_pb_summary.csv"}')
    print(f'TF-IDF por PB (imagenes individuales): {args.out_dir / "tfidf_por_pb"}')
    print(f'Figura complejidad: {args.out_dir / "complejidad_abstract_por_pb_violin.png"}')
    print(f'Wordcloud por PB (imagenes individuales): {args.out_dir / "wordcloud_por_pb"}')
    print(f'Wordcloud por PB (grid): {args.out_dir / "wordcloud_por_pb_grid.png"}')
    print(f'Tabla Wordcloud por PB: {args.out_dir / "wordcloud_por_pb_top_terms.csv"}')
    print(f'Similitud por terminos: {args.out_dir / "similitud_pb_por_terminos_tfidf.csv"}')
    print(f'Similitud por corpus completo: {args.out_dir / "similitud_pb_por_corpus_completo.csv"}')

    if tfidf_table.empty:
        print('AVISO: no se genero tabla TF-IDF (vacia). Revisa columnas de entrada.')
    if complexity_summary.empty:
        print('AVISO: no se genero resumen de complejidad (vacio).')
    if wordcloud_table.empty:
        print('AVISO: no se genero tabla de Wordcloud por PB (vacia).')
    if sim_terms_pairs.empty:
        print('AVISO: no se pudo calcular similitud por terminos TF-IDF.')
    if sim_corpus_pairs.empty:
        print('AVISO: no se pudo calcular similitud por corpus completo.')


if __name__ == '__main__':
    main()
