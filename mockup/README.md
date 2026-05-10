# UPV-EARTH Mockup v1

Esta carpeta contiene toda la aplicacion web (backend, frontend, infraestructura y docs de despliegue) para mantener limpio el repo principal.

## Contenido
- backend/: FastAPI + pipeline PDF -> PB.
- frontend/: Next.js + TypeScript + Tailwind.
- infra/nginx/: reverse proxy.
- data/uploads/: PDFs subidos.
- data/seed/: archivos auxiliares de seed.
- docker-compose.yml: orquestacion completa.
- .env.example: variables de entorno.
- AGENTS.md y DESIGN.md: arquitectura y sistema visual.

## Arranque recomendado (sin Docker)
Este proyecto se puede ejecutar completamente en local, ideal cuando Docker no esta disponible en el equipo.

1. Copiar variables:
   cp mockup/.env.example mockup/.env
2. Comprobar que Ollama esta activo en el host:
   ollama serve
3. Descargar el modelo (primera vez):
   ollama pull qwen2.5:14b

## Ejecucion local por LAN (misma WiFi)
1. Backend local (SQLite):
   export DATABASE_URL='sqlite:////home/sortmon/UPV_EARTH_PROYECTOIII/mockup/data/seed/upvearth_local.db'
   export UPLOAD_DIR='/home/sortmon/UPV_EARTH_PROYECTOIII/mockup/data/uploads'
   export PB_REFERENCE_CSV='/home/sortmon/UPV_EARTH_PROYECTOIII/corpus_PB/data/pb_reference.csv'
   export LLM_ENABLED='true'
   export OLLAMA_URL='http://127.0.0.1:11434/api/generate'
   export OLLAMA_MODEL_NAME='qwen2.5:14b'
   /home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
2. Frontend local:
   export PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/sortmon/UPV_EARTH_PROYECTOIII/.nodeenv/bin'
   export NEXT_PUBLIC_API_BASE_URL='/api/v1'
   export API_BASE_URL_INTERNAL='http://127.0.0.1:8000/api/v1'
   npm run dev -- --hostname 0.0.0.0 --port 3000
3. Obtener IP del host Linux:
   hostname -I
4. Acceder desde otro dispositivo de la misma red:
   http://IP_DEL_HOST:3000

## Seed del corpus UPV
1. Ejecutar seed inicial:
   docker compose -f mockup/docker-compose.yml --env-file mockup/.env exec backend python -m scripts.seed_corpus

## Precomputo de EDA y embeddings
Los KPIs del AED y los embeddings SPECTER2 se precalculan una sola vez para que el
dashboard, la pagina /analysis y la busqueda de similares respondan en milisegundos.
Si cambias el corpus o el modelo de embeddings vuelve a ejecutar:

   cd mockup/backend
   DATABASE_URL='sqlite:////home/sortmon/UPV_EARTH_PROYECTOIII/mockup/data/seed/upvearth_local.db' \
   PB_REFERENCE_CSV='/home/sortmon/UPV_EARTH_PROYECTOIII/corpus_PB/data/pb_reference.csv' \
   /home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/python -m scripts.precompute_eda
   /home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/python -m scripts.precompute_embeddings

Genera tres artefactos en `mockup/data/seed/precomputed/`:
- `eda.json` (KPIs, distribuciones, top keywords/journals, drop reasons, cobertura)
- `embeddings.npy` (matriz (N, dim) float32 normalizada)
- `embeddings_meta.json` (doc_id, titulo, anio, journal, abstract, PB, etc.)

El backend los detecta automaticamente al arrancar. Los servicios `corpus_quality` y
`similarity_search` los usan como cache; si no existen, calculan en caliente como
fallback. El estado se ve en `/api/v1/analytics/index-status` (campo `source`:
`precomputed` o `computed`) y en el panel "Calidad del corpus para embeddings" del
dashboard.

## URL interna
- Acceso inicial por IP interna:
  http://158.42.94.34

## Qwen / Ollama
- El pipeline de subida de PDF invoca Qwen 2.5:14b por defecto.
- Variables relevantes:
   - `LLM_ENABLED=true` (poner `false` para desactivar)
    - `OLLAMA_URL=http://127.0.0.1:11434/api/generate` (ejecucion local)
    - `OLLAMA_URL=http://ollama:11434/api/generate` (solo en Docker Compose)
    - `OLLAMA_MODEL_NAME=qwen2.5:14b`
   - `LLM_TEMPERATURE=0.0`
- El resultado del LLM se incorpora al `explanation_text` del resultado PB y se registra en eventos del job (`llm_reasoning`).

## Docker (opcional)
Si Docker vuelve a estar disponible en el equipo, se puede usar `mockup/docker-compose.yml`.
En ese modo, `docker-compose.yml` ya fuerza `OLLAMA_URL=http://ollama:11434/api/generate` para el backend.

## Nuevos endpoints analiticos
- `GET /api/v1/analytics/keywords/global?limit=12`
- `GET /api/v1/analytics/keywords/pb/{pb_code}?limit=12`
- `GET /api/v1/analytics/papers/{paper_id}/comparison`
- `GET /api/v1/jobs/{job_id}/events?limit=200` (eventos del pipeline + metricas runtime CPU/RAM/GPU)

## Chatbot RAG (UPV-EARTH)
El chatbot del dashboard, la pagina de subida y el detalle de paper es un sistema RAG
estricto. NO clasifica PBs ni decide similitud: esa logica vive en `embedding_service`,
`similarity_search` (SPECTER2 + numpy/FAISS) y `pb_inference`. El LLM solo explica,
resume y conversa sobre resultados ya calculados.

Endpoints:
- `GET  /api/v1/chat/health` -> estado del servidor LLM (enabled, available, modelo).
- `POST /api/v1/chat`        -> respuesta sincrona en JSON.
- `POST /api/v1/chat/stream` -> streaming SSE (eventos `meta`/`token`/`done`/`error`).

Variables relevantes (ver `.env.example`):
- `LLM_ENABLED=true|false` (si `false`, la UI muestra "Chatbot no disponible" y el
  resto sigue funcionando con normalidad).
- `LLM_BASE_URL=http://localhost:8001/v1` (endpoint compatible OpenAI).
- `LLM_MODEL=qwen3-8b-instruct`
- `LLM_API_KEY=local-key`
- `LLM_REQUEST_TIMEOUT=120`, `LLM_MAX_TOKENS=512`, `CHAT_TEMPERATURE=0.2`

### Levantar un LLM local opcional (sin Docker, sin sudo)

Recomendacion 1 (preferida): vLLM con Qwen3-8B Instruct o Llama 3.1 8B Instruct.

```
/home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/pip install vllm
/home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/python -m vllm.entrypoints.openai.api_server \
   --model Qwen/Qwen3-8B-Instruct \
   --served-model-name qwen3-8b-instruct \
   --port 8001
```

Recomendacion 2 (fallback ligero, sin GPU): llama-cpp-python en modo servidor
con un modelo GGUF cuantizado (Q4_K_M va bien en CPU).

```
/home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/pip install "llama-cpp-python[server]"
/home/sortmon/UPV_EARTH_PROYECTOIII/.venv/bin/python -m llama_cpp.server \
   --model /ruta/qwen3-8b-instruct-q4_k_m.gguf \
   --model_alias qwen3-8b-instruct \
   --host 0.0.0.0 --port 8001
```

Ambas opciones exponen `http://localhost:8001/v1/chat/completions` y son compatibles
con la cabecera `Authorization: Bearer <LLM_API_KEY>`. Si el servidor LLM no
esta arriba, el chatbot detecta el fallo via `/api/v1/chat/health` y la UI muestra
el banner "Chatbot no disponible" sin romper el resto de la plataforma.

## Notas de rutas
- El stack usa datos reales del repo padre en modo solo lectura:
  - ../data/corpus -> /app/data/corpus
  - ../corpus_PB -> /app/corpus_PB
- Uploads y seed de runtime se guardan dentro de mockup/data.
