# Flujo de extracción del corpus mixto (1000 documentos)

## Resumen

El flujo principal está en [pipeline/extract_corpus.py](../pipeline/extract_corpus.py). Procesa una muestra aleatoria de 1000 PDF en 3 bloques, descarga cada bloque con `rclone`, extrae texto y metadatos, filtra y deduplica registros, y escribe dos CSV finales:

- `data/corpus/corpus_1000_clean.csv`
- `data/corpus/corpus_1000_traceability.csv`

La idea es separar claramente dos cosas:

- el corpus final limpio, listo para análisis;
- la trazabilidad completa de qué se descartó y por qué.

## Entradas

- `muestras/listado_pdfs.txt`: inventario plano generado con `rclone lsf`.
- `muestras/muestra_seleccionada_1000.csv`: manifiesto de la muestra aleatoria elegida.
- `upv_drive:`: remoto desde el que se descargan los PDFs.

## Salidas

### CSV final limpio

`data/corpus/corpus_1000_clean.csv` contiene solo los registros que pasan los filtros.

Columnas principales:

- `doc_id`
- `title`
- `abstract`
- `clean_abstract`
- `year`
- `doi`
- `source`
- `authors`
- `keywords`
- `journal`
- `language`
- `top_terms_no_stopwords`

### CSV de trazabilidad

`data/corpus/corpus_1000_traceability.csv` contiene tanto lo aceptado como lo descartado, con el motivo del filtro.

Columnas adicionales importantes:

- `file_name`
- `pb_folder`
- `source_folder`
- `full_text`
- `language_confidence`
- `abstract_length`
- `clean_abstract_length`
- `dedupe_key`
- `filter_status`
- `filter_reason`
- `quality_flag`

## Qué hace el pipeline

### 1. Construcción de muestra

El script lee `muestras/listado_pdfs.txt`, toma 1000 rutas al azar y crea un manifiesto reproducible en `muestras/muestra_seleccionada_1000.csv`.

### 2. Descarga en 3 bloques

La muestra se divide en 3 bloques. Cada bloque se descarga con una sola llamada a `rclone copy` usando `--files-from`.

Esto reduce el coste de hacer una descarga por documento.

### 3. Extracción por PDF

Para cada archivo PDF:

- se extrae el texto completo de todas las páginas;
- se toma un preview de las 2 primeras páginas para localizar abstract y keywords;
- se obtienen título, DOI, año, autores y revista si es posible;
- se calculan las palabras más repetidas sin stopwords;
- se detecta idioma del abstract.

### 4. Limpieza del abstract

Se generan dos campos:

- `abstract`: texto detectado en el bloque de abstract o, si no existe, una aproximación heurística;
- `clean_abstract`: versión normalizada del abstract.

### 5. Filtros aplicados

Después de extraer el registro, el script decide si se conserva o se descarta.

Filtros principales:

- abstract vacío;
- abstract demasiado corto, con umbral mínimo de 500 caracteres;
- idioma distinto de inglés;
- duplicados por DOI;
- si no hay DOI, duplicados por coincidencia fuerte de título + año.

Cada descarte queda anotado en `filter_reason`.

### 6. Trazabilidad

Los registros descartados no se pierden: se escriben en `data/corpus/corpus_1000_traceability.csv` con la razón exacta del descarte.

## Keywords

La columna `keywords` se detecta sobre el texto crudo del preview antes de normalizar espacios. Esto permite conservar saltos de línea y la estructura del bloque de metadatos.

El detector busca variantes frecuentes como:

- `Keywords`
- `Key words`
- `Index Terms`
- `Palabras clave`
- `Subject terms`
- `Descriptors`
- variantes en otros idiomas cuando aparecen en la cabecera

## Stopwords

Ahora se usa `nltk.corpus.stopwords` como base, porque es más mantenible que una lista manual grande y cubre mejor inglés y español.

Se añade además un pequeño conjunto de palabras de dominio que no aportan contenido semántico en este corpus:

- `doi`, `http`, `https`, `www`
- `abstract`, `keywords`, `introduction`
- y otros términos de estructura editorial

## Por qué NLTK es mejor aquí

- evita mantener una lista manual larga;
- permite usar stopwords por idioma;
- hace el pipeline más claro y más fácil de ajustar;
- deja el código concentrado en la lógica del corpus, no en listas estáticas.

## Notebook

El notebook [notebooks/01_document_extraction.ipynb](../notebooks/01_document_extraction.ipynb) se mantiene como verificación del CSV final y de la trazabilidad. No es el flujo principal de procesamiento.

## Archivos que se consideran obsoletos

La versión unificada hace innecesarios los scripts separados de pruebas y el explorador de Drive antiguo:

- `explorar_drive.py`
- `extraccion_muestra.py`
- `extraccion_primeras_paginas.py`
- `extraccion_texto_completo.py`

También se consideran temporales o generados y pueden eliminarse cuando no se necesiten:

- `__pycache__/`
- `tmp_pdf/`
- `muestra_pdfs/`
- `upv_earth_proyectoiii.egg-info/`
- `y`

## Cómo ejecutar

```bash
python pipeline/extract_corpus.py
```

## Nota operativa

Si se cambia el tamaño de muestra, los bloques de descarga o los filtros, conviene volver a generar el CSV limpio y el de trazabilidad para mantener la consistencia entre resultados y documentación.
