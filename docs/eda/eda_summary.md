# EDA del corpus limpio

- Documentos procesados: **44970**
- Documentos con abstract no vacío (trazabilidad): **44593**
- Documentos finales tras filtros: **31634**

## Longitud de abstracts (abstract_norm)
- mean_chars: **1608.60**
- median_chars: **1484.00**
- p10_chars: **640.00**
- p25_chars: **1030.00**
- p75_chars: **2002.00**
- p90_chars: **2501.70**

## Calidad y nulos (corpus final)
- year: **1.83%** nulos
- doi: **20.70%** nulos
- journal: **10.81%** nulos
- keywords: **42.61%** nulos
- authors: **0.18%** nulos
- abstract_norm: **0.02%** nulos

## Fuentes
- rclone_drive: **31634**

## Sesgos / huecos detectados (trazabilidad)
- abstract_too_short<500: **11744**
- abstract_empty|language_unknown: **377**
- duplicate_title_year: **118**
- duplicate_doi: **117**
- language_not_english:fr: **100**
- abstract_too_short<500|duplicate_title_year: **87**
- language_not_english:es: **80**
- abstract_too_short<500|language_low_confidence:0.71: **78**
- language_not_english:pt: **48**
- abstract_too_short<500|language_not_english:de: **44**

## Top términos (unigramas)
- climate: 28346
- change: 21554
- water: 17870
- global: 14430
- land: 14174
- changes: 13188
- surface: 11288
- aerosol: 10937
- ocean: 10642
- environmental: 10516
- system: 10467
- species: 9770
- carbon: 9145
- temperature: 8961
- university: 8932
- atmospheric: 7993
- systems: 7963
- effects: 7943
- ozone: 7796
- conditions: 7709

## Top términos (bigramas)
- climate change: 13774
- ocean acidification: 2054
- land cover: 1815
- united states: 1768
- air quality: 1650
- boundary layer: 1364
- sustainable development: 1337
- remote sensing: 1244
- global warming: 1228
- organic matter: 1181
- earth system: 1151
- global climate: 1118
- biomass burning: 1098
- organic carbon: 1064
- ecosystem services: 1032
- aerosol optical: 1003
- surface temperature: 984
- land surface: 977
- greenhouse gas: 951
- regional climate: 897