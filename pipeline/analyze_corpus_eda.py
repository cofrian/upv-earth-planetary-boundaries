import argparse
import re
import unicodedata
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Anchored to the repository root so the script runs from any working directory.
BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_CSV = BASE_DIR / 'data' / 'corpus' / 'corpus_1000_clean.csv'
TRACE_CSV = BASE_DIR / 'data' / 'corpus' / 'corpus_1000_traceability.csv'
OUT_DIR = BASE_DIR / 'docs' / 'eda'
ENRICHED_CSV = BASE_DIR / 'data' / 'corpus' / 'corpus_1000_clean_enriched.csv'

EDITORIAL_PATTERNS = [
    r'(?i)published by[^.]*\.?',
    r'(?i)correspondence to[^.]*\.?',
    r'(?i)copyright[^.]*\.?',
    r'(?i)received:\s*[^.]*\.?',
    r'(?i)accepted:\s*[^.]*\.?',
    r'(?i)specialty section:\s*[^.]*\.?',
    r'(?i)citation:\s*[^.]*\.?',
    r'(?i)author manuscript[^.]*\.?',
    r'(?i)open access[^.]*\.?',
    r'(?i)creative commons[^.]*\.?',
    r'(?i)competing interests?[^.]*\.?',
    r'(?i)key\s*words?\s*:?',
    r'(?i)index\s+terms?\s*:?',
    r'(?i)doi:\s*10\.[^\s]+',
    r'http[s]?://\S+',
]

try:
    from nltk.corpus import stopwords as nltk_stopwords
    import nltk

    try:
        BASE_STOPWORDS = set(nltk_stopwords.words('english')) | set(nltk_stopwords.words('spanish'))
    except LookupError:
        nltk.download('stopwords', quiet=True)
        BASE_STOPWORDS = set(nltk_stopwords.words('english')) | set(nltk_stopwords.words('spanish'))
except Exception:
    BASE_STOPWORDS = set()

CUSTOM_STOPWORDS = {
    'the', 'and', 'for', 'with', 'this', 'that', 'from', 'were', 'are', 'was', 'have', 'has', 'had',
    'into', 'their', 'there', 'than', 'then', 'when', 'where', 'which', 'while', 'within', 'without',
    'using', 'used', 'use', 'also', 'can', 'may', 'might', 'more', 'most', 'some', 'such', 'over',
    'between', 'through', 'about', 'across', 'during', 'results', 'result', 'study', 'paper', 'article',
    'data', 'method', 'methods', 'model', 'models', 'analysis', 'based', 'show', 'shows', 'shown',
    'high', 'low', 'new', 'one', 'two', 'three', 'four', 'five', 'first', 'second', 'third', 'both',
    'these', 'those', 'each', 'other', 'onto', 'per', 'via', 'its', 'our', 'your', 'they', 'them',
    'you', 'we', 'his', 'her', 'not', 'but', 'all', 'any', 'due', 'doi', 'http', 'https', 'www',
    'com', 'org', 'edu', 'introduction', 'abstract', 'keywords', 'index', 'terms',
    'be', 'been', 'being', 'am', 'is', 'will',
    'key', 'words', 'open', 'access', 'competing', 'interests', 'author', 'authors',
    'et', 'al',
    'del', 'las', 'los', 'una', 'uno', 'unos', 'unas', 'para', 'por', 'con', 'sin', 'sobre', 'entre',
    'desde', 'hasta', 'como', 'tambien', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos',
    'esas', 'fue', 'fueron', 'ser', 'son', 'han', 'hace', 'hacer', 'hacia', 'segun',
    'datos', 'estudio', 'resultados', 'metodo', 'metodos', 'analisis', 'introduccion', 'resumen',
    'palabras', 'clave'
}

AUXILIARY_NOISE_STOPWORDS = {
    'be', 'been', 'being', 'am', 'is', 'are', 'was', 'were',
    'do', 'does', 'did', 'done',
    'will', 'would', 'should', 'could', 'might', 'must', 'shall', 'can', 'may',
    'get', 'gets', 'got', 'getting',
    'make', 'makes', 'made', 'making',
    'using', 'used', 'use',
    'however', 'therefore', 'thus', 'although',
    'paper', 'study', 'studies', 'article', 'research',
    'introduction', 'abstract', 'keyword', 'keywords', 'index', 'terms',
    'author', 'authors', 'et', 'al',
}

THEMATIC_NOISE_STOPWORDS = {
    'time', 'different', 'well', 'significant', 'important', 'potential', 'large',
    'present', 'observed', 'total', 'various', 'several', 'among', 'including',
    'based', 'according', 'results', 'result', 'show', 'shows', 'shown', 'suggest',
    'suggests', 'found', 'findings', 'approach', 'approaches', 'methodology',
    'analysis', 'analyses', 'data', 'new', 'high', 'low', 'future', 'past', 'current',
    'under', 'across', 'within', 'without',
    'long', 'term', 'series',
}

STOPWORDS = BASE_STOPWORDS | CUSTOM_STOPWORDS | AUXILIARY_NOISE_STOPWORDS | THEMATIC_NOISE_STOPWORDS


def fold_token(token: str) -> str:
    value = unicodedata.normalize('NFKD', token)
    return ''.join(ch for ch in value if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ''
    value = str(text)
    value = unicodedata.normalize('NFKC', value)
    value = value.replace('\u00ad', ' ')
    value = value.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    value = value.replace('\r', ' ').replace('\n', ' ')
    for pattern in EDITORIAL_PATTERNS:
        value = re.sub(pattern, ' ', value)
    value = re.sub(r'\s+', ' ', value)
    value = re.sub(r'\s*([,;:.!?])\s*', r'\1 ', value)
    return value.strip(' .;:-')


def lex_clean(text: str) -> str:
    if not text:
        return ''
    tokens = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text.lower())
    tokens = [fold_token(t) for t in tokens]
    tokens = [t for t in tokens if t not in STOPWORDS]
    return ' '.join(tokens)


def top_ngrams(series: pd.Series, ngram_size=1, topn=30):
    counter = Counter()
    for text in series.fillna(''):
        toks = text.split()
        if ngram_size == 1:
            counter.update(toks)
        else:
            for i in range(len(toks) - ngram_size + 1):
                counter[' '.join(toks[i:i + ngram_size])] += 1
    return pd.DataFrame(counter.most_common(topn), columns=['term', 'count'])


def parse_args():
    parser = argparse.ArgumentParser(description='Genera corpus enriquecido y salidas EDA.')
    parser.add_argument('--input', type=Path, default=CLEAN_CSV, help='CSV limpio de entrada')
    parser.add_argument('--trace', type=Path, default=TRACE_CSV, help='CSV de trazabilidad')
    parser.add_argument('--output', type=Path, default=ENRICHED_CSV, help='CSV enriquecido de salida')
    parser.add_argument('--out-dir', type=Path, default=OUT_DIR, help='Directorio de salidas EDA')
    return parser.parse_args()


def main():
    args = parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    clean = pd.read_csv(args.input)
    trace = pd.read_csv(args.trace)

    clean['abstract_raw'] = clean['abstract'].fillna('')
    clean['abstract_norm'] = clean['abstract_raw'].map(normalize_text)
    clean['clean_abstract_lex'] = clean['abstract_norm'].map(lex_clean)
    clean['abstract_norm_len'] = clean['abstract_norm'].str.len()

    # Reordenar columnas para dejar las nuevas junto al abstract.
    cols = list(clean.columns)
    ordered = [
        'doc_id', 'title', 'abstract_raw', 'abstract_norm', 'clean_abstract_lex',
        'abstract', 'clean_abstract', 'year', 'doi', 'source', 'authors', 'keywords',
        'journal', 'language', 'top_terms_no_stopwords', 'abstract_norm_len'
    ]
    clean = clean[[c for c in ordered if c in cols]]
    clean.to_csv(args.output, index=False)

    # EDA base
    n_processed = len(trace)
    n_valid_abstract = int((trace['abstract_length'].fillna(0) >= 1).sum())
    n_final = len(clean)

    year_series = pd.to_numeric(clean['year'], errors='coerce').dropna().astype(int)
    year_dist = year_series.value_counts().sort_index().rename_axis('year').reset_index(name='n')
    year_dist.to_csv(args.out_dir / 'year_distribution.csv', index=False)

    lengths = clean['abstract_norm_len']
    desc = {
        'mean_chars': float(lengths.mean()),
        'median_chars': float(lengths.median()),
        'p10_chars': float(lengths.quantile(0.10)),
        'p25_chars': float(lengths.quantile(0.25)),
        'p75_chars': float(lengths.quantile(0.75)),
        'p90_chars': float(lengths.quantile(0.90)),
    }

    null_table = pd.DataFrame({
        'field': ['year', 'doi', 'journal', 'keywords', 'authors', 'abstract_norm'],
        'null_pct': [
            clean['year'].isna().mean() * 100,
            clean['doi'].isna().mean() * 100,
            clean['journal'].isna().mean() * 100,
            clean['keywords'].isna().mean() * 100,
            clean['authors'].isna().mean() * 100,
            (clean['abstract_norm'].str.len() == 0).mean() * 100,
        ],
    })
    null_table.to_csv(args.out_dir / 'null_table.csv', index=False)

    source_dist = clean['source'].fillna('NA').value_counts().rename_axis('source').reset_index(name='n')
    source_dist.to_csv(args.out_dir / 'source_distribution.csv', index=False)

    top_uni = top_ngrams(clean['clean_abstract_lex'], ngram_size=1, topn=50)
    top_bi = top_ngrams(clean['clean_abstract_lex'], ngram_size=2, topn=50)
    top_uni.to_csv(args.out_dir / 'top_unigrams.csv', index=False)
    top_bi.to_csv(args.out_dir / 'top_bigrams.csv', index=False)

    # Sesgos/huecos desde trazabilidad
    drop = trace[trace['filter_status'] == 'dropped'].copy()
    reason_counts = drop['filter_reason'].fillna('').value_counts().rename_axis('reason_combo').reset_index(name='n')
    reason_counts.to_csv(args.out_dir / 'drop_reason_combinations.csv', index=False)

    # Gráficas
    plt.style.use('default')

    if not year_dist.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(year_dist['year'], year_dist['n'], marker='o', linewidth=1)
        ax.set_title('Publicaciones por año (corpus final)')
        ax.set_xlabel('Año')
        ax.set_ylabel('Nº de abstracts')
        fig.tight_layout()
        fig.savefig(args.out_dir / 'publicaciones_por_anio.png', dpi=150)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(lengths, bins=30, edgecolor='black', alpha=0.8)
    ax.set_title('Distribución de longitud de abstracts normalizados')
    ax.set_xlabel('Longitud (caracteres)')
    ax.set_ylabel('Frecuencia')
    fig.tight_layout()
    fig.savefig(args.out_dir / 'distribucion_longitud_abstracts.png', dpi=150)
    plt.close(fig)

    # Resumen Markdown para el PDF
    md = []
    md.append('# EDA del corpus limpio\n')
    md.append(f'- Documentos procesados: **{n_processed}**')
    md.append(f'- Documentos con abstract no vacío (trazabilidad): **{n_valid_abstract}**')
    md.append(f'- Documentos finales tras filtros: **{n_final}**\n')

    md.append('## Longitud de abstracts (abstract_norm)')
    for k, v in desc.items():
        md.append(f'- {k}: **{v:.2f}**')

    md.append('\n## Calidad y nulos (corpus final)')
    for _, row in null_table.iterrows():
        md.append(f"- {row['field']}: **{row['null_pct']:.2f}%** nulos")

    md.append('\n## Fuentes')
    for _, row in source_dist.iterrows():
        md.append(f"- {row['source']}: **{int(row['n'])}**")

    md.append('\n## Sesgos / huecos detectados (trazabilidad)')
    top_reasons = reason_counts.head(10)
    for _, row in top_reasons.iterrows():
        md.append(f"- {row['reason_combo']}: **{int(row['n'])}**")

    if not top_uni.empty:
        md.append('\n## Top términos (unigramas)')
        md.extend([f"- {t}: {int(c)}" for t, c in top_uni.head(20).itertuples(index=False)])

    if not top_bi.empty:
        md.append('\n## Top términos (bigramas)')
        md.extend([f"- {t}: {int(c)}" for t, c in top_bi.head(20).itertuples(index=False)])

    (args.out_dir / 'eda_summary.md').write_text('\n'.join(md), encoding='utf-8')

    print('EDA completado.')
    print(f'CSV enriquecido: {args.output}')
    print(f'Reportes en: {args.out_dir}')


if __name__ == '__main__':
    main()
