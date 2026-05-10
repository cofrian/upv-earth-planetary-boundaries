## Plan Refinado: Plataforma UPV-EARTH - Entrega Final

### 1) Objetivo real del producto
Construir una plataforma web que no parezca una demo técnica, sino un producto científico serio, visualmente cuidado y metodológicamente defendible para la entrega final.

La plataforma debe permitir:
1. Explorar el corpus UPV ya procesado con una experiencia premium.
2. Entender con claridad la calidad del corpus y el criterio metodológico de filtrado.
3. Subir un PDF nuevo, extraer abstract, validar longitud, generar embedding con SPECTER2 y recuperar papers similares por contenido.
4. Mostrar análisis exploratorio del corpus con gráficos útiles, interpretación breve y trazabilidad completa.

### 2) Contexto del repositorio que hay que respetar
Usar como base real del proyecto estos activos del repo:
1. `data/corpus/master_corpus_mixto_1000_clean_enriched.csv` como fuente principal para embeddings y analítica.
2. `data/corpus/master_corpus_mixto_1000_clean.csv` como fuente mínima.
3. `data/corpus/master_corpus_mixto_1000_traceability.csv` como auditoría de filtros y descartes.
4. `corpus_PB/data/pb_reference.csv` como referencia semántica de los 9 Planetary Boundaries.
5. `docs/bert_embeddings_inputs.md` como guía de columnas válidas para embeddings.
6. `docs/eda/eda_summary.md` como referencia de métricas reales ya calculadas.
7. `mockup/` como implementación actual a mejorar, no como algo a desechar.

Hechos de trabajo que deben reflejarse en la UI y el AED:
1. El corpus final es distinto del corpus bruto.
2. Existe un corte metodológico obligatorio por longitud de abstract.
3. Los abstracts cortos deben distinguirse claramente de los válidos para embeddings.
4. El análisis de año debe ignorar valores imposibles o mal parseados.

### 3) Definiciones metodológicas obligatorias
No mezclar nunca estas capas:
1. Corpus bruto: todos los PDFs/papers procesados.
2. Corpus con abstract: papers donde se detectó algún abstract.
3. Corpus válido: papers con abstract limpio y suficiente contenido.
4. Corpus para embeddings: papers con `abstract_char_len > 500` y texto semánticamente limpio.
5. Corpus indexado: papers con embedding SPECTER2 generado e incluidos en FAISS.

La UI debe mostrar estas cifras por separado y con nombres explícitos.

El texto canónico para embeddings debe quedar claro como:
1. `title + clean_abstract_semantic`
2. Filtro principal: `abstract_char_len > 500`

Si la implementación actual usa otro nombre intermedio, se puede mapear internamente, pero la capa de producto debe comunicar ese criterio de forma consistente.

### 4) Resultado de producto esperado
La aplicación final debe ofrecer estas experiencias:
1. Dashboard principal con KPIs, ratios, calidad del corpus y visuales de alto nivel.
2. Página de exploración del corpus con filtros y tabla profesional.
3. Página de subida de paper con estados por etapa, validación del abstract y explicación clara.
4. Página de resultados con papers similares por contenido y criterio de validez para el corpus.
5. Página de AED / análisis exploratorio del corpus con bloques temáticos, gráficos y texto interpretativo.

### 5) Enfoque visual y de UX
La dirección visual debe ser:
1. Dark mode principal.
2. Acentos verde esmeralda / verde científico.
3. Tarjetas limpias, bordes sutiles y buen espaciado.
4. Tipografía clara, técnica y con jerarquía fuerte.
5. Tablas bien diseñadas, legibles y útiles para análisis científico.
6. Estados de carga elegantes, sin spinners pobres ni pantallas vacías genéricas.
7. Errores comprensibles, con mensajes accionables.
8. Visualizaciones integradas con coherencia cromática y narrativa.

La app debe parecer una herramienta real para el proyecto, no un prototipo de hackathon.

### 6) Diseño de pantallas

#### 6.1 Dashboard principal
Debe incluir:
1. KPI cards de corpus bruto, corpus con abstract, corpus válido, corpus para embeddings y corpus indexado.
2. Porcentaje de corpus válido.
3. Longitud media y mediana del abstract.
4. Papers con DOI, keywords, journals distintos y rango temporal cubierto.
5. Gráficas de evolución temporal, calidad de corpus y metadatos.
6. Bloque específico de “Calidad del corpus para embeddings”.

#### 6.2 Página de exploración del corpus
Debe permitir:
1. Buscar y filtrar por año, journal, PB, fuente, DOI, keywords y longitud de abstract.
2. Ordenar y paginar resultados.
3. Ver una tabla premium con jerarquía visual.
4. Abrir detalle de paper sin perder contexto.

#### 6.3 Página de subida de paper
Debe mostrar con claridad:
1. Estado de subida.
2. Estado de extracción del PDF.
3. Abstract detectado.
4. Validación del abstract: longitud, umbral de 500 caracteres, calidad estimada.
5. Generación de embedding con SPECTER2.
6. Recuperación de similares por contenido.
7. Resumen del abstract.
8. PBs estimados si ya existe inferencia.

#### 6.4 Página de resultados del paper subido
Debe incluir una tarjeta de criterio metodológico con:
1. abstract detectado: sí / no.
2. longitud del abstract.
3. supera 500 caracteres: sí / no.
4. apto para embeddings: sí / no.

Además:
1. Sección “Papers similares por contenido” muy cuidada visualmente.
2. Explicación explícita de que los resultados comparan el embedding SPECTER2 del paper subido con los embeddings SPECTER2 del corpus UPV.
3. Muestra de título, año, journal, DOI, score, abstract preview y PBs principales si existen.

#### 6.5 Página de AED / análisis exploratorio del corpus
Debe tener:
1. Resumen ejecutivo arriba.
2. Filtros por año, journal, PB y longitud de abstract.
3. Gráficos organizados por bloques temáticos.
4. Tablas descargables o al menos reutilizables.
5. Una breve interpretación debajo de cada gráfico.

### 7) Módulos del AED que deben aparecer
#### 7.1 Distribución temporal
1. Papers por año.
2. Evolución temporal de papers válidos.
3. Evolución temporal de papers con abstract > 500 caracteres.

#### 7.2 Calidad del corpus
1. Histograma de longitud de abstracts.
2. Boxplot o distribución equivalente.
3. Proporción de abstracts válidos vs descartados.
4. Tabla de completitud de metadatos.

#### 7.3 Metadatos
1. Top journals.
2. Top keywords.
3. Papers por fuente si existe la columna `source`.
4. Porcentaje con DOI.
5. Porcentaje con keywords.
6. Porcentaje con journal.

#### 7.4 Texto
1. Top términos frecuentes sobre `clean_abstract_lex`.
2. Top bigramas.
3. Nube de palabras solo si aporta valor, nunca como gráfico principal.
4. Distribución de número de palabras por abstract.

#### 7.5 Planetary Boundaries
Si existen scores o etiquetas PB:
1. Ranking de PBs más frecuentes.
2. Distribución de papers por PB.
3. Evolución temporal por PB.
4. Co-ocurrencia entre PBs.
5. Matriz de calor PB vs año si hay suficiente muestra.

### 8) Bloque obligatorio: Calidad del corpus para embeddings
Crear una sección específica con ese título, donde quede muy visible:
1. Cuántos papers tienen texto suficiente para embedding.
2. Cuántos se descartaron por abstract corto.
3. Longitud media de `title + clean_abstract_semantic`.
4. Distribución aproximada de tokens.
5. Número de embeddings generados correctamente.
6. Número de papers incluidos en FAISS.
7. Cobertura del índice respecto al corpus válido.

La intención de ese bloque es que cualquiera entienda de un vistazo qué parte del corpus sirve realmente para SPECTER2.

### 9) Backend y API
Integrar o ampliar una capa de analytics coherente con el backend actual del mockup.

Mantener la convención de API versionada ya usada en el proyecto, preferentemente bajo `/api/v1`.

Endpoints deseables o equivalentes:
1. `GET /api/v1/analytics/summary`
2. `GET /api/v1/analytics/abstract-lengths`
3. `GET /api/v1/analytics/papers-by-year`
4. `GET /api/v1/analytics/metadata-completeness`
5. `GET /api/v1/analytics/top-keywords`
6. `GET /api/v1/analytics/pb-distribution`
7. `GET /api/v1/analytics/embedding-coverage`
8. `GET /api/v1/analytics/downloads`
9. `GET /api/v1/papers`
10. `GET /api/v1/papers/{paper_id}`
11. `POST /api/v1/uploads/pdf`
12. `GET /api/v1/jobs/{job_id}`
13. `GET /api/v1/papers/{paper_id}/comparison`

Si la estructura final cambia, conservar la coherencia con la API actual, no inventar una segunda convención sin necesidad.

### 10) Exportación y trazabilidad
La sección de AED debe permitir consultar o descargar, al menos conceptualmente:
1. `master_corpus_clean.csv` o el CSV maestro equivalente del repositorio.
2. Resumen de filtros aplicados.
3. Número de papers descartados por cada criterio.
4. Listado de papers sin abstract.
5. Listado de papers con abstract corto.
6. Listado de papers indexados en FAISS.

Si la descarga directa no se implementa, dejar al menos la estructura preparada y documentar cómo generar esos artefactos desde el backend o scripts.

### 11) Flujo de subida y resultados
El resultado del upload debe presentarse en una secuencia comprensible:
1. Subida.
2. Extracción del PDF.
3. Detección del abstract.
4. Validación de longitud y calidad.
5. Generación del embedding.
6. Clasificación PB / inferencia de PBs estimados.
7. Búsqueda de similares.
8. Resumen y resultado final.

Cada paso debe tener estados claros y errores legibles.

### 12) Diseño de la sección de papers similares
La sección “Papers similares por contenido” debe verse como un módulo principal, no como un apéndice.

Cada paper similar debe mostrar:
1. Título.
2. Año.
3. Journal.
4. DOI si existe.
5. Score de similitud.
6. Abstract preview.
7. PBs principales si están disponibles.

Debajo o al lado del bloque debe aparecer una explicación breve que deje claro el criterio de similitud.

### 13) Consideraciones técnicas importantes
1. Usar SPECTER2 como backbone principal para embeddings en esta fase.
2. Preparar FAISS como índice operativo para vecinos cercanos.
3. Mantener el modo LLM como opcional o complementario, nunca como requisito del núcleo funcional.
4. Preservar la trazabilidad entre corpus bruto, filtrado, embeddings e índice.
5. No mezclar métricas de corpus bruto con corpus válido ni con corpus indexado.
6. No presentar tablas o gráficos sin contexto mínimo.

### 14) Stack y arquitectura esperada
Respetar el stack del mockup y su orientación actual:
1. Backend: FastAPI modular.
2. Frontend: Next.js + React + TypeScript + Tailwind.
3. Persistencia: PostgreSQL.
4. Proxy: Nginx.
5. Despliegue: Docker Compose.

La prioridad no es solo que funcione, sino que la experiencia final sea defendible para una demo académica de alto nivel.

### 15) Entregables que debe producir la iteración
1. UI/UX renovada y consistente en todo el producto.
2. Dashboard premium con AED completo.
3. Página específica de análisis exploratorio del corpus.
4. Flujo de upload y resultados mucho más claro.
5. Sección de similares por contenido bien resuelta.
6. Endpoints analíticos preparados para el frontend.
7. Documentación breve de métricas, filtros y exportaciones.
8. Alineación explícita entre corpus bruto, corpus válido y corpus indexado.

### 16) Criterios de aceptación
La mejora se considera correcta si:
1. El dashboard se percibe como un producto profesional.
2. El AED permite entender calidad, composición y cobertura del corpus.
3. El usuario entiende qué papers sirven para embeddings y por qué.
4. El upload muestra validación metodológica y no solo un resultado final.
5. Los papers similares se presentan con jerarquía visual y contexto metodológico.
6. La aplicación usa una estética moderna dark-first con acentos verdes y buena legibilidad.
7. La información de corpus bruto, corpus válido, corpus para embeddings y corpus indexado aparece separada.

### 17) Prioridades de implementación
1. Primero, mejorar la UI/UX global y la jerarquía visual.
2. Segundo, consolidar el AED completo con métricas y gráficos.
3. Tercero, reforzar el flujo de upload y resultados.
4. Cuarto, activar la experiencia de similares por contenido sobre SPECTER2 + FAISS.
5. Quinto, dejar exportación y trazabilidad bien documentadas.

### 18) Regla final de producto
Si hay que elegir entre añadir más complejidad técnica o mejorar claridad para la entrega final, priorizar siempre claridad, trazabilidad y calidad visual.
