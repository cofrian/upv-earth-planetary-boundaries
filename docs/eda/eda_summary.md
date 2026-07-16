# EDA del corpus limpio

- Documentos procesados: **1000**
- Documentos con abstract no vacío (trazabilidad): **994**
- Documentos finales tras filtros: **700**

## Longitud de abstracts (abstract_norm)
- mean_chars: **1608.83**
- median_chars: **1492.50**
- p10_chars: **687.20**
- p25_chars: **985.75**
- p75_chars: **2046.50**
- p90_chars: **2502.00**

## Calidad y nulos (corpus final)
- year: **1.29%** nulos
- doi: **23.29%** nulos
- journal: **10.14%** nulos
- keywords: **41.71%** nulos
- authors: **0.29%** nulos
- abstract_norm: **0.00%** nulos

## Fuentes
- rclone_drive: **700**

## Sesgos / huecos detectados (trazabilidad)
- abstract_too_short<500: **269**
- abstract_empty|language_unknown: **6**
- abstract_too_short<500|language_not_english:fr: **3**
- duplicate_doi: **3**
- abstract_too_short<500|language_not_english:de: **2**
- abstract_too_short<500|language_low_confidence:0.71: **2**
- language_low_confidence:0.55: **2**
- abstract_too_short<500|language_not_english:uk: **1**
- abstract_too_short<500|language_low_confidence:0.55: **1**
- abstract_too_short<500|language_low_confidence:0.43: **1**

## Top términos (unigramas)
- climate: 670
- change: 466
- water: 340
- global: 339
- land: 334
- changes: 285
- surface: 241
- species: 232
- environmental: 231
- system: 224
- aerosol: 223
- carbon: 218
- ocean: 214
- emissions: 208
- ozone: 207
- atmospheric: 186
- systems: 186
- conditions: 185
- temperature: 177
- effects: 169

## Top términos (bigramas)
- climate change: 277
- land cover: 58
- remote sensing: 44
- boundary layer: 39
- air quality: 38
- ocean acidification: 38
- organic matter: 35
- earth system: 32
- united states: 30
- organic carbon: 30
- global climate: 29
- regional climate: 26
- global warming: 26
- aerosol optical: 26
- land change: 23
- black carbon: 23
- greenhouse gas: 23
- ozone depletion: 23
- tree species: 23
- north atlantic: 22