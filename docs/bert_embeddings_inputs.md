# CSV para BERT embeddings

Este documento deja explícito qué CSV del repositorio se usa para la fase de embeddings con BERT.

## Archivo recomendado

- [data/corpus/corpus_1000_clean_enriched.csv](../data/corpus/corpus_1000_clean_enriched.csv)

Motivo: contiene tanto el texto original como columnas de limpieza útiles para preparar el input.

## Columnas recomendadas para embeddings

1. `abstract_norm`
- Texto recomendado por defecto para embeddings.
- Está normalizado (espacios/saltos/caracteres editoriales), manteniendo contenido semántico.

2. `abstract` o `abstract_raw`
- Úsalas solo si quieres conservar el texto más cercano al original sin normalización adicional.

3. `keywords`
- Útil como señal auxiliar o para enriquecer prompts/metadata.

## Columnas de soporte (no como input directo de embeddings)

- `clean_abstract_lex`: limpieza léxica orientada a conteo de términos/EDA.
- `top_terms_no_stopwords`: resumen de términos por documento para análisis descriptivo.

Estas columnas son útiles para análisis exploratorio, no para representar el texto completo en BERT.

## Validación de stopwords en términos por documento

Estado validado en esta sesión:

- En [data/corpus/corpus_1000_clean.csv](../data/corpus/corpus_1000_clean.csv), `top_terms_no_stopwords` no contiene stopwords básicas como `are`, `was`, `were`, `been`, `is`, `be`.
- En [data/corpus/corpus_1000_clean_enriched.csv](../data/corpus/corpus_1000_clean_enriched.csv), mismo resultado.

## Otros CSV de contexto

- [data/corpus/corpus_1000_traceability.csv](../data/corpus/corpus_1000_traceability.csv): auditoría de filtros (kept/dropped), no es input de embeddings.
- [docs/eda/top_unigrams.csv](eda/top_unigrams.csv) y [docs/eda/top_bigrams.csv](eda/top_bigrams.csv): salidas EDA para interpretación temática.
- [docs/eda/semantic_topic_clusters.csv](eda/semantic_topic_clusters.csv): salida de agrupación semántica, útil para análisis posterior, no para generar embeddings base.
