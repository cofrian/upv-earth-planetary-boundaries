#!/usr/bin/env bash
# =============================================================================
# UPV-EARTH · launch.sh
# Arranca toda la pila en local: Ollama + backend FastAPI + frontend Next.js.
#
#   ./launch.sh           -> arranca en foreground (Ctrl+C detiene todo)
#   ./launch.sh stop      -> detiene los servicios lanzados con este script
#   ./launch.sh status    -> muestra el estado actual
#
# Requiere haber ejecutado antes:  ./setup.sh
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
BACKEND_DIR="$ROOT_DIR/mockup/backend"
FRONTEND_DIR="$ROOT_DIR/mockup/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"
PID_DIR="$RUNTIME_DIR/pids"
LOG_DIR="$RUNTIME_DIR/logs"

DB_FILE="$ROOT_DIR/mockup/data/seed/upvearth_local.db"
UPLOAD_DIR="$ROOT_DIR/mockup/data/uploads"
PB_REFERENCE_CSV="$ROOT_DIR/corpus_PB/data/pb_reference.csv"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:14b}"

mkdir -p "$PID_DIR" "$LOG_DIR" "$UPLOAD_DIR" "$(dirname "$DB_FILE")"

log()  { printf "\033[1;36m[run ]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ ok ]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[err ]\033[0m %s\n" "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid; pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

port_in_use() {
  local port="$1"
  if have ss; then ss -ltn 2>/dev/null | grep -q ":$port "
  elif have lsof; then lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else return 1
  fi
}

preflight() {
  [[ -x "$VENV_DIR/bin/python" ]] || { err "venv ausente en $VENV_DIR. Ejecuta ./setup.sh primero."; exit 1; }
  [[ -d "$FRONTEND_DIR/node_modules" ]] || { err "node_modules ausente. Ejecuta ./setup.sh primero."; exit 1; }
  have ollama || warn "Ollama no encontrado en PATH. El chatbot y el scoring LLM no funcionarán."
}

start_ollama() {
  if curl -fsS --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ok "Ollama ya está corriendo"
    return
  fi
  have ollama || { warn "Saltando Ollama (no instalado)"; return; }
  log "Arrancando Ollama..."
  nohup ollama serve >"$LOG_DIR/ollama.log" 2>&1 &
  echo $! > "$PID_DIR/ollama.pid"
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      ok "Ollama listo (PID $(cat "$PID_DIR/ollama.pid"))"; return
    fi
    sleep 1
  done
  warn "Ollama no respondió. Revisa $LOG_DIR/ollama.log"
}

start_backend() {
  if is_running "$PID_DIR/backend.pid"; then
    ok "Backend ya en ejecución (PID $(cat "$PID_DIR/backend.pid"))"
    return
  fi
  if port_in_use "$BACKEND_PORT"; then
    warn "Puerto $BACKEND_PORT ocupado por otro proceso. Saltando arranque del backend."
    return
  fi
  log "Arrancando backend FastAPI en puerto $BACKEND_PORT..."
  (
    cd "$BACKEND_DIR"
    nohup env \
      DATABASE_URL="sqlite:///$DB_FILE" \
      UPLOAD_DIR="$UPLOAD_DIR" \
      PB_REFERENCE_CSV="$PB_REFERENCE_CSV" \
      EMBEDDINGS_MODEL_NAME="${EMBEDDINGS_MODEL_NAME:-sentence-transformers/allenai-specter}" \
      LLM_ENABLED="${LLM_ENABLED:-true}" \
      OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434/api/generate}" \
      OLLAMA_MODEL_NAME="${OLLAMA_MODEL_NAME:-$OLLAMA_MODEL}" \
      LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.0}" \
      LLM_BASE_URL="${LLM_BASE_URL:-http://127.0.0.1:11434/v1}" \
      LLM_MODEL="${LLM_MODEL:-$OLLAMA_MODEL}" \
      LLM_API_KEY="${LLM_API_KEY:-ollama}" \
      LLM_REQUEST_TIMEOUT="${LLM_REQUEST_TIMEOUT:-180}" \
      LLM_MAX_TOKENS="${LLM_MAX_TOKENS:-512}" \
      CHAT_TEMPERATURE="${CHAT_TEMPERATURE:-0.2}" \
      "$VENV_DIR/bin/python" -m uvicorn app.main:app \
        --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
      >>"$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
  )
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 1 "http://127.0.0.1:$BACKEND_PORT/api/v1/health" >/dev/null 2>&1; then
      ok "Backend listo en http://localhost:$BACKEND_PORT  (PID $(cat "$PID_DIR/backend.pid"))"
      return
    fi
    sleep 1
  done
  warn "Backend no respondió tras 60s. Revisa $LOG_DIR/backend.log"
}

start_frontend() {
  if is_running "$PID_DIR/frontend.pid"; then
    ok "Frontend ya en ejecución (PID $(cat "$PID_DIR/frontend.pid"))"
    return
  fi
  if port_in_use "$FRONTEND_PORT"; then
    warn "Puerto $FRONTEND_PORT ocupado por otro proceso. Saltando arranque del frontend."
    return
  fi
  log "Arrancando frontend Next.js en puerto $FRONTEND_PORT..."
  (
    cd "$FRONTEND_DIR"
    nohup env \
      NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-/api/v1}" \
      API_BASE_URL_INTERNAL="${API_BASE_URL_INTERNAL:-http://127.0.0.1:$BACKEND_PORT/api/v1}" \
      npm run dev -- --hostname "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >>"$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
  )
  for _ in $(seq 1 90); do
    if curl -fsS --max-time 1 "http://127.0.0.1:$FRONTEND_PORT" >/dev/null 2>&1; then
      ok "Frontend listo en http://localhost:$FRONTEND_PORT  (PID $(cat "$PID_DIR/frontend.pid"))"
      return
    fi
    sleep 1
  done
  warn "Frontend no respondió tras 90s. Revisa $LOG_DIR/frontend.log"
}

stop_one() {
  local pid_file="$1" name="$2"
  if ! is_running "$pid_file"; then
    log "$name no estaba corriendo."
    rm -f "$pid_file"; return
  fi
  local pid; pid="$(cat "$pid_file")"
  log "Deteniendo $name (PID $pid)..."
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || { rm -f "$pid_file"; ok "$name detenido."; return; }
    sleep 1
  done
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
  ok "$name forzado a detenerse."
}

cmd_stop() {
  stop_one "$PID_DIR/frontend.pid" Frontend
  stop_one "$PID_DIR/backend.pid"  Backend
  stop_one "$PID_DIR/ollama.pid"   Ollama
}

cmd_status() {
  is_running "$PID_DIR/ollama.pid"   && ok "Ollama   RUNNING (PID $(cat "$PID_DIR/ollama.pid"))"   || warn "Ollama   STOPPED"
  is_running "$PID_DIR/backend.pid"  && ok "Backend  RUNNING (PID $(cat "$PID_DIR/backend.pid"))"  || warn "Backend  STOPPED"
  is_running "$PID_DIR/frontend.pid" && ok "Frontend RUNNING (PID $(cat "$PID_DIR/frontend.pid"))" || warn "Frontend STOPPED"
  echo
  echo "Logs: $LOG_DIR/{ollama,backend,frontend}.log"
}

cleanup() {
  echo
  log "Cerrando (Ctrl+C)..."
  cmd_stop
  exit 0
}

cmd_start() {
  preflight
  start_ollama
  start_backend
  start_frontend
  echo
  ok "Pila UPV-EARTH lista:"
  echo "  · Frontend:  http://localhost:$FRONTEND_PORT"
  echo "  · Backend:   http://localhost:$BACKEND_PORT  (health: /api/v1/health)"
  echo "  · Ollama:    http://localhost:11434"
  echo "  · Logs:      $LOG_DIR/"
  echo
  log "Pulsa Ctrl+C para detener todos los servicios."
  trap cleanup INT TERM
  while true; do
    sleep 5
    is_running "$PID_DIR/backend.pid"  || { err "Backend caído. Revisa $LOG_DIR/backend.log"; cmd_stop; exit 1; }
    is_running "$PID_DIR/frontend.pid" || { err "Frontend caído. Revisa $LOG_DIR/frontend.log"; cmd_stop; exit 1; }
  done
}

case "${1:-start}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  status)  cmd_status ;;
  restart) cmd_stop; cmd_start ;;
  *)
    cat <<EOF
Uso: ./launch.sh [start|stop|status|restart]
  start    arranca Ollama + backend + frontend (Ctrl+C detiene todo)
  stop     detiene los servicios lanzados con este script
  status   muestra el estado actual
  restart  reinicia todo
EOF
    exit 1
    ;;
esac
