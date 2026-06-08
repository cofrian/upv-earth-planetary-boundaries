"""
Análisis de similitud entre PB usando embeddings semánticos (sentence-transformers).
Complemento al script de gráficos M2.
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


def parse_args():
    parser = argparse.ArgumentParser(description='Analiza similitud entre PB por embeddings.')
    parser.add_argument('--clean', type=Path, default=Path('data/corpus/master_corpus_mixto_1000_clean_enriched.csv'))
    parser.add_argument('--trace', type=Path, default=Path('data/corpus/master_corpus_mixto_1000_traceability.csv'))
    parser.add_argument('--out-dir', type=Path, default=Path('docs/eda'))
    parser.add_argument('--model', type=str, default='all-MiniLM-L6-v2', help='Modelo de sentence-transformers')
    return parser.parse_args()


def normalize_pb(pb_value) -> str:
    if pd.isna(pb_value):
        return 'Unknown'
    return str(pb_value).strip()


def get_ordered_pb_list(pb_series):
    pb_order = [
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
    ordered_pb = [pb for pb in pb_order if pb in set(pb_series)]
    missing_pb = [pb for pb in sorted(pb_series.dropna().unique()) if pb not in ordered_pb]
    return ordered_pb + missing_pb


def save_similarity_outputs(sim_df, out_dir, stem, title):
    """Guarda matriz, heatmap y top pairs."""
    sim_df.to_csv(out_dir / f'{stem}.csv', index=True)

    plt.figure(figsize=(10.5, 8.5))
    sns.heatmap(sim_df, annot=True, fmt='.2f', cmap='YlGnBu', vmin=0, vmax=1, square=True)
    plt.title(title, fontsize=14)
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


def build_dataset(clean_path, trace_path):
    """Construye dataset con mapeo PB."""
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


def main():
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Cargando dataset...")
    df = build_dataset(args.clean, args.trace)
    print(f"Filas usadas: {len(df)}")

    # Preparar corpus
    corpus = df.copy()
    corpus['text_for_embeddings'] = (
        corpus['clean_abstract'].fillna('')
        + ' '
        + corpus['keywords'].fillna('')
    )
    corpus = corpus[corpus['text_for_embeddings'].str.len() > 10]

    print(f"Cargando modelo {args.model}...")
    model = SentenceTransformer(args.model)

    pb_order = get_ordered_pb_list(corpus['pb_folder'])
    embeddings_list = []
    labels = []
    
    print("Codificando textos por PB...")
    for pb_idx, pb in enumerate(pb_order, 1):
        subset = corpus[corpus['pb_folder'] == pb]
        if len(subset) == 0:
            continue

        print(f"  [{pb_idx}/9] {pb}... ({len(subset)} docs)", end='', flush=True)
        texts = subset['text_for_embeddings'].tolist()
        embeddings = model.encode(texts, show_progress_bar=False)
        centroid = embeddings.mean(axis=0)
        embeddings_list.append(centroid)
        labels.append(pb)
        print(" OK")

    if not embeddings_list:
        print("ERROR: No se pudieron codificar textos.")
        return

    print("Calculando similitud coseno...")
    embeddings_mat = np.vstack(embeddings_list)
    sim = cosine_similarity(embeddings_mat)
    sim_df = pd.DataFrame(sim, index=labels, columns=labels)

    print("Guardando outputs...")
    top_pairs = save_similarity_outputs(
        sim_df,
        args.out_dir,
        stem='similitud_pb_por_embeddings_semanticos',
        title='Similitud entre PB por embeddings semánticos (sentence-transformers)',
    )

    print(f"\n✓ Similitud guardada en: {args.out_dir / 'similitud_pb_por_embeddings_semanticos.csv'}")
    print(f"✓ Heatmap guardado en: {args.out_dir / 'similitud_pb_por_embeddings_semanticos.png'}")
    print(f"✓ Top pares guardados en: {args.out_dir / 'similitud_pb_por_embeddings_semanticos_top_pairs.csv'}")
    
    print("\nTop 5 pares más similares (por embeddings):")
    for idx, row in top_pairs.head(5).iterrows():
        print(f"  {row['pb_a']} <-> {row['pb_b']}: {row['similarity']:.3f}")


if __name__ == '__main__':
    main()
