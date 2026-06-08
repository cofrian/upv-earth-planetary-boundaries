## Plan Unificado: Plataforma Web UPV-EARTH - Entrega Final

Construir una plataforma web modular (FastAPI + Next.js + PostgreSQL + Docker Compose + Nginx) desplegable en red interna de la UPV, pensada como entrega final del proyecto: debe verse como un producto científico serio, visualmente premium, claro y defendible.

La plataforma debe integrar:
1. Dashboard principal con KPIs, calidad del corpus y visuales de alto nivel.
2. Explorador del corpus con filtros, ordenación, paginación y detalle.
3. Página de subida de paper con estados de proceso y validación metodológica.
4. Página de resultados con resumen, PBs estimados y papers similares por contenido.
5. Página de análisis exploratorio del corpus con gráficas, contexto e interpretación breve.

La experiencia visual debe ser dark-first, con acentos verde esmeralda / verde científico, tarjetas limpias, buena jerarquía tipográfica, tablas legibles, estados de carga elegantes y errores comprensibles.

## Criterios metodológicos obligatorios
1. Distinguir siempre corpus bruto, corpus con abstract, corpus válido, corpus para embeddings e índice FAISS.
2. El criterio principal para embeddings es `abstract_char_len > 500`.
3. El texto canónico para embeddings es `title + clean_abstract_semantic`.
4. No mezclar métricas de corpus bruto con corpus válido o indexado.
5. Mostrar de forma explícita qué papers sirven realmente para SPECTER2 y por qué.

## Requisitos de producto
1. El dashboard debe parecer una herramienta real, no una demo técnica pobre.
2. El AED debe ser completo, visualmente interesante y metodológicamente defendible.
3. La sección de similares por contenido debe ser un módulo principal, no un apéndice.
4. El flujo de subida debe permitir entender rápido si el paper es válido para el corpus.
5. La UI debe priorizar claridad, trazabilidad y utilidad para la entrega final.

**Steps**
1. Fase 0 - Base del monorepo y configuración compartida
1.1. Crear estructura de proyecto separada en `backend/`, `frontend/`, `infra/nginx/`, `data/seed/`, `docs/`.
1.2. Definir variables y contratos de entorno en `.env.example` para DB, almacenamiento de uploads, límites de tamaño PDF, puertos internos, flags de LLM opcional.
1.3. Estandarizar configuración para ejecución en servidor interno (host binding 0.0.0.0 en backend, frontend servido por Nginx).

2. Fase 1 - Arquitectura backend y dominio (bloquea fases 2, 3 y 4)
2.1. Implementar FastAPI con módulos: `pdf_ingestion`, `metadata_extraction`, `abstract_extraction`, `text_cleaning`, `embedding_service`, `pb_inference`, `summarization`, `paper_repository`, `analytics_service`, `api`.
2.2. Reutilizar funciones probadas del pipeline actual para extracción/limpieza/metadatos y trazabilidad (adaptadas a servicios desacoplados).
2.3. Definir capa de configuración y dependencias para modo sin LLM por defecto y backend extensible para proveedor LLM futuro.
2.4. Implementar validación segura de uploads PDF (mime + extensión + tamaño + nombre seguro + ruta aislada).

3. Fase 2 - Modelo de datos PostgreSQL y persistencia (depende de 2.1)
3.1. Crear esquema relacional inicial:
- `papers` (metadatos + textos + rutas + estado)
- `pb_results` (score por PB, top PB, threshold, versión modelo)
- `processing_jobs` (estado, etapa, tiempos, error)
- `corpus_metrics_cache` (agregados EDA precalculados)
- `ingestion_events` (auditoría de operaciones)
3.2. Diseñar migraciones y seed inicial desde `master_corpus_mixto_1000_clean_enriched.csv` y trazabilidad asociada.
3.3. Dejar preparado el esquema para embeddings persistidos y vector index (tablas reservadas si se necesita ampliar la capacidad).

4. Fase 3 - Pipeline de inferencia de nuevo PDF (depende de 2 y 3)
4.1. Endpoint de subida crea `processing_job` y almacena PDF en repositorio seguro.
4.2. Procesamiento asíncrono con `BackgroundTasks` por simplicidad operativa.
4.3. Flujo por etapas: ingestión PDF -> extracción de texto (PyMuPDF) -> detección abstract -> validación de longitud -> limpieza -> embedding SPECTER2 -> similitud con 9 PB -> recuperación de papers similares -> clasificación top + secundarios -> resumen fallback (primeras 3-4 frases).
4.4. Persistir resultados y exponer endpoint de estado para polling frontend.
4.5. Estandarizar errores por etapa para UI legible y soporte operativo.

5. Fase 4 - API de analítica y exploración del corpus (paralela con fase 3 tras tener fase 2)
5.1. Endpoints dashboard: KPIs globales, distribución por PB, por año, calidad de corpus, papers por journal/source y cobertura de embeddings.
5.2. Endpoints exploración: búsqueda full-text básica + filtros `year`, `journal`, `pb`, `doi`, `keywords`, ordenación y paginación.
5.3. Endpoint detalle paper: título, abstract, metadatos, scores PB, resumen y trazabilidad mínima.
5.4. Endpoint de resultados de job para paper subido, con payload unificado para renderizado de resultados.
5.5. Endpoints AED: resumen, abstract-lengths, papers-by-year, metadata-completeness, top-keywords, pb-distribution, embedding-coverage y descargas/trazabilidad.
5.6. Endpoint de similitud por contenido con top-k vecinos y metadatos del corpus UPV.

6. Fase 5 - Frontend Next.js + Tailwind + diseño premium técnico (depende de 4 y 5)
6.1. Definir sistema visual dark-first inspirado en Vercel/Supabase/Linear con acento verde esmeralda/verde-gris en `DESIGN.md`.
6.2. Implementar vistas:
- Dashboard analítico con tarjetas y gráficas consistentes
- Explorador de papers con filtros + tabla + detalle
- Página específica de análisis exploratorio del corpus
- Flujo de subida PDF con estados (upload/parsing/inferencia/resumen/error)
- Resultado de análisis de paper subido
- Sección de papers similares por contenido muy bien diseñada
6.3. Garantizar responsive desktop/móvil y estados vacíos/carga/error no genéricos.

7. Fase 6 - Infraestructura y despliegue interno (paralela con fase 5 tras tener backend/frontend base)
7.1. Crear `docker-compose.yml` con servicios: `db`, `backend`, `frontend` (si aplica build separado), `nginx`.
7.2. Configurar backend escuchando en 0.0.0.0 dentro de contenedor.
7.3. Configurar Nginx reverse proxy para URL interna objetivo `158.42.94.34` (evolucionable a hostname), límites de subida, timeouts y headers forward.
7.4. Añadir guía de despliegue para red universitaria (puertos, firewall, arranque, comprobaciones de salud, logs).

8. Fase 7 - Documentación contractual y entregables (depende de fases 1-6)
8.1. Redactar `AGENTS.md` con objetivo, arquitectura modular, flujo de datos, ejecución, despliegue y roadmap por fases.
8.2. Redactar `DESIGN.md` con principios visuales, componentes, tokens, reglas de gráficos/tablas/espaciado y estados UX.
8.3. Actualizar `README.md` con instalación, variables, seed del corpus UPV, ejecución por Docker Compose y acceso por URL interna.
8.4. Documentar la experiencia de similitud por contenido, criterios de corpus para embeddings y trazabilidad de filtros/descartes.

9. Similares por contenido y posicionamiento en el corpus
9.1. Definir interfaces de `similarity_search` y contratos API versionados para top-k vecinos por SPECTER2.
9.2. Especificar estrategia con embeddings persistidos + FAISS + posicionamiento relativo en corpus.
9.3. Dejar checklist de calibración, cobertura del índice y trazabilidad de similitud.

**Relevant files**
- `/home/sortmon/UPV_EARTH_PROYECTOIII/extraccion_corpus_mixto.py` - reutilizar extracción de abstract, limpieza, evaluación de calidad y trazabilidad.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/extraccion_corpus_mixto_balanced.py` - referencia para lógica PB estratificada y consistencia de columnas.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/analisis_corpus_eda.py` - reutilizar enriquecimiento textual y métricas agregadas para dashboard.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/data/corpus/master_corpus_mixto_1000_clean_enriched.csv` - seed inicial de `papers` y métricas.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/data/corpus/master_corpus_mixto_1000_traceability.csv` - seed de trazabilidad/calidad para analítica.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/corpus_PB/data/pb_reference.csv` - base semántica para embeddings de los 9 PB y scoring.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/docs/eda/eda_summary.md` - referencia de KPIs iniciales del dashboard.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/docs/flujo_extraccion_1000.md` - referencia del flujo de procesamiento y estados.
- `/home/sortmon/UPV_EARTH_PROYECTOIII/README.md` - actualizar para operación completa y despliegue interno.

**Verification**
1. Verificar arranque de stack completo con `docker compose up -d` y healthchecks OK de backend/db/nginx.
2. Verificar acceso interno desde otro equipo de la red a `http://158.42.94.34` (o hostname definido) y carga correcta del frontend.
3. Ejecutar seed inicial y comprobar conteos consistentes con corpus fuente.
4. Probar subida de PDF válido y confirmar transición de estados de job hasta `completed`.
5. Probar PDF inválido/sobredimensionado y confirmar error controlado y seguro.
6. Validar dashboard: KPIs y distribuciones coinciden con agregados del dataset.
7. Validar exploración: filtros, ordenación, paginación y detalle de paper funcionales.
8. Validar inferencia PB sin LLM habilitado (modo por defecto) y resumen fallback activo.
9. Validar que el sistema sigue operativo cuando el proveedor LLM opcional está deshabilitado.

**Decisions**
- Autenticación: sin login por defecto, solo red interna.
- Asincronía: `FastAPI BackgroundTasks` por simplicidad y tiempo de entrega.
- Núcleo PB: similitud de embeddings abstract vs definiciones PB.
- Embeddings de corpus: SPECTER2 + FAISS como flujo central.
- Resumen sin LLM: fallback simple de primeras 3-4 frases del abstract limpio.
- Carga inicial: seed automático desde CSV enriquecido actual.
- URL interna objetivo inicial: `158.42.94.34`.
- Alcance actual: incluye visualización de similares por contenido y analítica del corpus.

**Further Considerations**
1. Seguridad de acceso sin login: mantenerlo solo en red interna segmentada; para siguiente iteración evaluar login básico o SSO.
2. Evolución asíncrona: si sube volumen de carga, migrar de `BackgroundTasks` a cola dedicada (`Celery + Redis`) sin romper API.
3. Gobierno del modelo PB: versionar embeddings, thresholds y métricas de calidad para trazabilidad científica reproducible.