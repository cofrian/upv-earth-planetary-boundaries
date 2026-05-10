#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
PID_DIR="$RUNTIME_DIR/pids"
LOG_DIR="$RUNTIME_DIR/logs"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

BACKEND_DIR="$ROOT_DIR/mockup/backend"
FRONTEND_DIR="$ROOT_DIR/mockup/frontend"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

NODE_BIN_CANDIDATES=(
  "/home/sortmon/.local/nodeenv-upv-earth/bin"
  "$ROOT_DIR/.nodeenv/bin"
  "/home/sortmon/.nodeenv/bin"
)

mkdir -p "$PID_DIR" "$LOG_DIR"

pick_node_bin() {
  for candidate in "${NODE_BIN_CANDIDATES[@]}"; do
    if [[ -x "$candidate/npm" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

port_in_use() {
  local port="$1"
  ss -ltn 2>/dev/null | grep -q ":$port "
}

start_backend() {
  # Evita conflictos si hay un uvicorn anterior levantado fuera del script.
  pkill -f 'uvicorn app.main:app' 2>/dev/null || true

  if is_running "$BACKEND_PID_FILE"; then
    echo "Backend ya está en ejecución (PID $(cat "$BACKEND_PID_FILE"))."
    return 0
  fi

  echo "Iniciando backend..."
  (
    cd "$BACKEND_DIR"
    nohup env \
      DATABASE_URL="sqlite:////home/sortmon/UPV_EARTH_PROYECTOIII/mockup/data/seed/upvearth_local.db" \
      UPLOAD_DIR="/home/sortmon/UPV_EARTH_PROYECTOIII/mockup/data/uploads" \
      PB_REFERENCE_CSV="/home/sortmon/UPV_EARTH_PROYECTOIII/corpus_PB/data/pb_reference.csv" \
      EMBEDDINGS_MODEL_NAME="sentence-transformers/allenai-specter" \
      LLM_ENABLED="true" \
      OLLAMA_URL="http://127.0.0.1:11434/api/generate" \
      OLLAMA_MODEL_NAME="qwen2.5:14b" \
      LLM_TEMPERATURE="0.0" \
      LLM_BASE_URL="http://127.0.0.1:11434/v1" \
      LLM_MODEL="qwen2.5:14b" \
      LLM_API_KEY="ollama" \
      LLM_REQUEST_TIMEOUT="180" \
      LLM_MAX_TOKENS="512" \
      CHAT_TEMPERATURE="0.2" \
      "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      >>"$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
  )

  sleep 1
  if is_running "$BACKEND_PID_FILE"; then
    echo "Backend levantado (PID $(cat "$BACKEND_PID_FILE"))."
  elif port_in_use 8000; then
    echo "Backend activo en puerto 8000 (proceso externo al script)."
  else
    echo "No se pudo iniciar backend. Revisa $LOG_DIR/backend.log"
    return 1
  fi
}

start_frontend() {
  # Evita conflictos si hay un Next anterior levantado fuera del script.
  pkill -f 'next dev|next-server|next start' 2>/dev/null || true

  if is_running "$FRONTEND_PID_FILE"; then
    echo "Frontend ya está en ejecución (PID $(cat "$FRONTEND_PID_FILE"))."
    return 0
  fi

  local node_bin
  if ! node_bin="$(pick_node_bin)"; then
    echo "No se encontró npm en rutas conocidas."
    echo "Rutas revisadas: ${NODE_BIN_CANDIDATES[*]}"
    return 1
  fi

  echo "Iniciando frontend usando npm de: $node_bin"
  (
    cd "$FRONTEND_DIR"
    nohup env \
      PATH="$node_bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      NEXT_PUBLIC_API_BASE_URL="/api/v1" \
      API_BASE_URL_INTERNAL="http://127.0.0.1:8000/api/v1" \
      npm run dev -- --hostname 0.0.0.0 --port 3000 \
      >>"$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )

  sleep 2
  if is_running "$FRONTEND_PID_FILE"; then
    echo "Frontend levantado (PID $(cat "$FRONTEND_PID_FILE"))."
  elif port_in_use 3000; then
    echo "Frontend activo en puerto 3000 (proceso externo al script)."
  else
    echo "No se pudo iniciar frontend. Revisa $LOG_DIR/frontend.log"
    return 1
  fi
}

stop_service() {
  local pid_file="$1"
  local name="$2"

  if ! is_running "$pid_file"; then
    echo "$name no está en ejecución."
    rm -f "$pid_file"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"
  echo "Deteniendo $name (PID $pid)..."
  kill "$pid" 2>/dev/null || true

  for _ in {1..10}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$pid_file"
      echo "$name detenido."
      return 0
    fi
    sleep 1
  done

  echo "Forzando cierre de $name (PID $pid)..."
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
}

status() {
  if is_running "$BACKEND_PID_FILE"; then
    echo "Backend: RUNNING (PID $(cat "$BACKEND_PID_FILE"))"
  else
    echo "Backend: STOPPED"
  fi

  if is_running "$FRONTEND_PID_FILE"; then
    echo "Frontend: RUNNING (PID $(cat "$FRONTEND_PID_FILE"))"
  else
    echo "Frontend: STOPPED"
  fi

  echo "Logs backend: $LOG_DIR/backend.log"
  echo "Logs frontend: $LOG_DIR/frontend.log"
}

usage() {
  cat <<EOF
Uso: bash scripts/web_services.sh <start|stop|restart|status>

  start   Inicia backend (8000) y frontend (3000) en segundo plano
  stop    Detiene backend y frontend
  restart Reinicia ambos servicios
  status  Muestra estado y rutas de logs
EOF
}

cmd="${1:-}"
case "$cmd" in
  start)
    start_backend
    start_frontend
    ;;
  stop)
    stop_service "$FRONTEND_PID_FILE" "Frontend"
    stop_service "$BACKEND_PID_FILE" "Backend"
    ;;
  restart)
    stop_service "$FRONTEND_PID_FILE" "Frontend"
    stop_service "$BACKEND_PID_FILE" "Backend"
    start_backend
    start_frontend
    ;;
  status)
    status
    ;;
  *)
    usage
    exit 1
    ;;
esac
