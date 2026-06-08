# Organización del repositorio

Fecha: 2026-04-19

## Distribución actual

### Raíz del proyecto

- analisis_corpus_eda.py
- extraccion_corpus_mixto.py
- extraccion_corpus_mixto_balanced.py
- extraccion_documents.ipynb
- README.md
- pyproject.toml
- uv.lock

### data/

- data/corpus/
  - master_corpus_mixto_1000_clean.csv
  - master_corpus_mixto_1000_clean_enriched.csv
  - master_corpus_mixto_1000_traceability.csv
  - eval_gemma4_26b_advanced.csv
- data/log.txt
- data/log_balanced_run.txt
- data/prueba.txt

### docs/

- docs/bert_embeddings_inputs.md
- docs/flujo_extraccion_1000.md
- docs/MUESTREO_ESTRATIFICADO.md
- docs/ORGANIZACION_REPO.md
- docs/eda/
  - reportes EDA (tablas y figuras)
  - docs/eda/auditoria/
    - auditoria_muestra_final_real.md
    - muestra_final_missing_21.csv
    - muestra_final_dropped_283.csv
    - muestra_final_kept_696.csv
    - pb_distribucion_muestra_final_696.csv

### prompts/

- prompts/prompt.py
- prompts/contexto_agente_codigo_upv_earth_m_2.md
- prompts/test_auth.txt

### scripts/

- scripts/auxiliary/compare_sampling_methods.py
- scripts/auxiliary/prueba_luis.py

### corpus y muestras

- corpus_PB/
  - corpus de referencia PB (data, docs, references)
- muestras/
  - listado_pdfs.txt
  - muestra_seleccionada_1000.csv
  - muestra_seleccionada_1000_balanced.csv
  - _sample_paths.tmp
- muestra_pdfs/
  - PDFs descargados por PB y SDG

### carpetas de trabajo/entorno

- .venv/
- .git/
- __pycache__/

## Notas de orden

- Los CSV maestros del pipeline están centralizados en data/corpus.
- Los activos de prompts están agrupados en prompts.
- Los scripts auxiliares están agrupados en scripts/auxiliary.
- Los scripts principales de extracción y EDA se mantienen en la raíz para compatibilidad.

## Pendiente opcional de limpieza

- Existe una carpeta legacy de respaldo llamada "abstracts muestra 1" con copias antiguas de CSV. Se puede mover a una carpeta de archive/ o eliminar si ya no se necesita.
