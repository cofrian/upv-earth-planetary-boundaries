# Benchmark Embeddings PB (M2)

Este directorio contiene la parte de **Tarea 7 + Tarea 8** para clasificación de Planetary Boundaries (PB) sobre abstracts.

## Estado del repositorio (abril 2026)

- Se eliminaron los notebooks `fine_tuning.ipynb` heredados de otra asignatura para evitar confusión.
- `pb_backbones_benchmark.ipynb` estaba vacío y ahora se usa como lanzador para el benchmark PB.
- El pipeline operativo se implementa en:
  - `pb_backbones_benchmark.py`

## Qué hace el script

1. Carga corpus enriquecido (`abstract_norm`) y referencia PB.
2. Construye y evalúa:
  - Baseline 1 léxico (keywords PB).
  - Baseline 2 semántico simple (TF-IDF + coseno).
3. Ejecuta backbones embeddings:
  - `bert-base-uncased`
  - `roberta-base`
  - `allenai/scibert_scivocab_uncased`
4. Ajusta regla multilabel por `threshold + delta`.
5. Exporta métricas y predicciones.

## Comando recomendado

```bash
./.venv/bin/python nlp/bert_finetuning/pb_backbones_benchmark.py \
  --models bert-base-uncased,roberta-base,allenai/scibert_scivocab_uncased \
  --batch-size 24 \
  --max-length 256 \
  --fallback-top1
```

## Outputs

Se generan en:

- `nlp/bert_finetuning/outputs/backbone_comparison.csv`
- `nlp/bert_finetuning/outputs/<modelo>/metrics.json`
- `nlp/bert_finetuning/outputs/<modelo>/predictions_all_docs.csv`
- `nlp/bert_finetuning/outputs/<modelo>/predictions_validation.csv`

## Notas metodológicas

- Validación humana: 108 documentos.
- Intersección usable con el corpus limpio actual: 73 documentos.
- Esto está alineado con la trazabilidad de filtros (`corpus_1000_traceability.csv`).

## Siguiente ajuste recomendado

Para mejorar calidad semántica de RoBERTa, puedes probar un encoder de sentence-transformers basado en roberta (por ejemplo `sentence-transformers/all-distilroberta-v1`) en lugar de `roberta-base` puro.
