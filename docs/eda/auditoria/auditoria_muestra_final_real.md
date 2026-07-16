# Auditoría de muestra final real

Fecha: 2026-04-19

## Alcance

- Muestra seleccionada (balanceada): [muestras/muestra_seleccionada_1000_balanced.csv](../../../muestras/muestra_seleccionada_1000_balanced.csv)
- Trazabilidad de procesamiento: [data/corpus/corpus_1000_traceability.csv](../../../data/corpus/corpus_1000_traceability.csv)
- Corpus final limpio: [data/corpus/corpus_1000_clean.csv](../../../data/corpus/corpus_1000_clean.csv)

## Resultado global

- Seleccionados: 1000
- Procesados con trazabilidad: 979
- Finales válidos (kept): 696
- Descartados (dropped): 283
- No procesados (seleccionados sin fila en trazabilidad): 21

Comprobación de consistencia:

- IDs kept en trazabilidad = 696
- IDs únicos en corpus final limpio = 696
- Diferencia entre ambos conjuntos = 0

## Requisitos y no cumplimiento

Registros descartados por no cumplir criterios de calidad/filtro:

- abstract_too_short<500: 260
- abstract_empty|language_unknown: 6
- language_not_english: 8 (fr=4, es=1, ru=1, it=1, ro=1)
- language_low_confidence: 3 (0.57=2, 0.55=1)
- Combinaciones short+idioma: 7 (fr=2, pt=2, de=2, it=1, ro=1)

Nota: los conteos anteriores se solapan cuando hay razones combinadas en un mismo registro.

## Distribución PB

### Muestra seleccionada (1000)

- PB1 Climate Change: 112
- PB2 Ocean Acidification: 111
- PB3 Stratospheric Ozone Depletion: 111
- PB4 Biogeochemical Flows: 111
- PB5 Global Freshwater Use: 111
- PB6 Land System Change: 111
- PB7 Biosphere Integrity: 111
- PB8 Novel Entities: 111
- PB9 Atmospheric Aerosol Loading: 111

### Muestra final real kept (696)

- PB1 Climate Change: 83
- PB2 Ocean Acidification: 74
- PB3 Stratospheric Ozone Depletion: 79
- PB4 Biogeochemical Flows: 76
- PB5 Global Freshwater Use: 66
- PB6 Land System Change: 90
- PB7 Biosphere Integrity: 69
- PB8 Novel Entities: 76
- PB9 Atmospheric Aerosol Loading: 83

## Evidencias detalladas

- No procesados (21): [docs/eda/muestra_final_missing_21.csv](muestra_final_missing_21.csv)
- Descartados (283): [docs/eda/muestra_final_dropped_283.csv](muestra_final_dropped_283.csv)
- Válidos kept (696): [docs/eda/muestra_final_kept_696.csv](muestra_final_kept_696.csv)
- Distribución PB final (696): [docs/eda/pb_distribucion_muestra_final_696.csv](pb_distribucion_muestra_final_696.csv)
