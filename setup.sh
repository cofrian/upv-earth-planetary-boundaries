#!/usr/bin/env bash
# =============================================================================
# UPV-EARTH · setup.sh
# Bootstrap completo para Linux y macOS desde un SO sin nada instalado.
#
#   ./setup.sh   -> instala/verifica dependencias y prepara el proyecto
#   ./launch.sh  -> arranca backend + frontend + Ollama
#
# Idempotente: si algo ya está instalado, lo detecta y continúa.
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
FRONTEND_DIR="$ROOT_DIR/mockup/frontend"
BACKEND_DIR="$ROOT_DIR/mockup/backend"
ENV_FILE="$ROOT_DIR/mockup/.env"
ENV_EXAMPLE="$ROOT_DIR/mockup/.env.example"

PY_MIN_MAJOR=3
PY_MIN_MINOR=11
NODE_MIN_MAJOR=20
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:14b}"

# --- Helpers -----------------------------------------------------------------
log()  { printf "\033[1;36m[setup]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ ok ]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[err ]\033[0m %s\n" "$*" >&2; }

have() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
  local uname_s
  uname_s="$(uname -s)"
  case "$uname_s" in
    Linux*)   OS=linux ;;
    Darwin*)  OS=macos ;;
    MINGW*|MSYS*|CYGWIN*)
      err "Detectado Windows con shell tipo Unix. Usa ./setup.ps1 en PowerShell."
      exit 1 ;;
    *)
      err "Sistema operativo no soportado: $uname_s"; exit 1 ;;
  esac

  if [[ "$OS" == "linux" ]]; then
    if   have apt-get; then PKG=apt
    elif have dnf;     then PKG=dnf
    elif have pacman;  then PKG=pacman
    elif have zypper;  then PKG=zypper
    else
      warn "Gestor de paquetes no reconocido. Intentaré seguir, instala manualmente lo que falte."
      PKG=unknown
    fi
  else
    PKG=brew
  fi
  log "SO detectado: $OS (paquetes: $PKG)"
}

sudo_cmd() {
  if [[ $EUID -eq 0 ]]; then "$@"; else sudo "$@"; fi
}

# --- macOS: Homebrew ---------------------------------------------------------
ensure_brew() {
  [[ "$OS" == "macos" ]] || return 0
  if have brew; then ok "Homebrew presente"; return; fi
  log "Instalando Homebrew (puede pedir contraseña)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  ok "Homebrew instalado"
}

# --- Python 3.11 -------------------------------------------------------------
python_ok() {
  local p="$1"
  have "$p" || return 1
  "$p" - <<'PY' >/dev/null 2>&1 || return 1
import sys
sys.exit(0 if (sys.version_info[0] == 3 and sys.version_info[1] == 11) else 1)
PY
}

pick_python() {
  for p in python3.11 python3 python; do
    if python_ok "$p"; then PY_BIN="$p"; return 0; fi
  done
  return 1
}

install_python() {
  log "Instalando Python ${PY_MIN_MAJOR}.${PY_MIN_MINOR}..."
  case "$PKG" in
    apt)
      sudo_cmd apt-get update -y
      if ! sudo_cmd apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip; then
        warn "python3.11 no disponible en repos por defecto, añadiendo PPA deadsnakes..."
        sudo_cmd apt-get install -y software-properties-common
        sudo_cmd add-apt-repository -y ppa:deadsnakes/ppa
        sudo_cmd apt-get update -y
        sudo_cmd apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
      fi
      ;;
    dnf)     sudo_cmd dnf install -y python3.11 python3.11-devel python3-pip ;;
    pacman)  sudo_cmd pacman -Sy --noconfirm python python-pip ;;
    zypper)  sudo_cmd zypper install -y python311 python311-devel python311-pip ;;
    brew)    brew install python@3.11 && brew link --force --overwrite python@3.11 ;;
    *) err "Instala Python 3.11 manualmente y reintenta."; exit 1 ;;
  esac
}

ensure_python() {
  if pick_python; then
    ok "Python OK: $($PY_BIN --version) ($PY_BIN)"
    return
  fi
  install_python
  if pick_python; then
    ok "Python instalado: $($PY_BIN --version)"
  else
    err "No se pudo instalar Python 3.11"; exit 1
  fi
}

# --- Node.js 20 --------------------------------------------------------------
node_ok() {
  have node || return 1
  local v
  v="$(node -v 2>/dev/null | sed 's/^v//')"
  local major="${v%%.*}"
  [[ "$major" -ge "$NODE_MIN_MAJOR" ]]
}

install_node() {
  log "Instalando Node.js ${NODE_MIN_MAJOR}.x..."
  case "$PKG" in
    apt)
      curl -fsSL "https://deb.nodesource.com/setup_${NODE_MIN_MAJOR}.x" | sudo_cmd -E bash -
      sudo_cmd apt-get install -y nodejs
      ;;
    dnf)
      curl -fsSL "https://rpm.nodesource.com/setup_${NODE_MIN_MAJOR}.x" | sudo_cmd -E bash -
      sudo_cmd dnf install -y nodejs
      ;;
    pacman)  sudo_cmd pacman -Sy --noconfirm nodejs npm ;;
    zypper)  sudo_cmd zypper install -y nodejs20 npm20 ;;
    brew)    brew install node@${NODE_MIN_MAJOR} && brew link --force --overwrite node@${NODE_MIN_MAJOR} ;;
    *) err "Instala Node.js ${NODE_MIN_MAJOR}+ manualmente y reintenta."; exit 1 ;;
  esac
}

ensure_node() {
  if node_ok; then
    ok "Node OK: $(node -v)  ·  npm $(npm -v)"
    return
  fi
  install_node
  if node_ok; then
    ok "Node instalado: $(node -v)"
  else
    err "No se pudo instalar Node.js ${NODE_MIN_MAJOR}+"; exit 1
  fi
}

# --- Ollama ------------------------------------------------------------------
install_ollama() {
  log "Instalando Ollama..."
  if [[ "$OS" == "macos" ]]; then
    brew install ollama || curl -fsSL https://ollama.com/install.sh | sh
  else
    curl -fsSL https://ollama.com/install.sh | sh
  fi
}

ensure_ollama() {
  if have ollama; then
    ok "Ollama presente: $(ollama --version 2>/dev/null | head -n1 || echo 'instalado')"
    return
  fi
  install_ollama
  have ollama && ok "Ollama instalado" || { err "Fallo instalando Ollama"; exit 1; }
}

start_ollama_bg() {
  if curl -fsS --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ok "Servicio Ollama ya corriendo"
    return
  fi
  log "Levantando 'ollama serve' en segundo plano..."
  mkdir -p "$ROOT_DIR/.runtime/logs"
  nohup ollama serve >"$ROOT_DIR/.runtime/logs/ollama.log" 2>&1 &
  echo $! > "$ROOT_DIR/.runtime/pids/ollama.pid" 2>/dev/null || true
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      ok "Ollama listo"; return
    fi
    sleep 1
  done
  warn "Ollama no respondió en 30s; revisa $ROOT_DIR/.runtime/logs/ollama.log"
}

pull_model() {
  log "Comprobando modelo Ollama '$OLLAMA_MODEL' (puede ser una descarga grande)..."
  if ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -Fxq "$OLLAMA_MODEL"; then
    ok "Modelo '$OLLAMA_MODEL' ya descargado"
    return
  fi
  if ollama pull "$OLLAMA_MODEL"; then
    ok "Modelo '$OLLAMA_MODEL' descargado"
  else
    warn "No se pudo descargar '$OLLAMA_MODEL'. Podrás descargarlo más tarde con: ollama pull $OLLAMA_MODEL"
  fi
}

# --- Backend (Python venv + deps) -------------------------------------------
ensure_venv() {
  if [[ -L "$VENV_DIR" || -d "$VENV_DIR" ]]; then
    if [[ -x "$VENV_DIR/bin/python" ]]; then
      ok "venv existente en $VENV_DIR"
      return
    fi
    warn "Eliminando venv inválido en $VENV_DIR"
    rm -rf "$VENV_DIR"
  fi
  log "Creando venv en $VENV_DIR con $PY_BIN..."
  "$PY_BIN" -m venv "$VENV_DIR"
  ok "venv creado"
}

install_backend_deps() {
  log "Instalando dependencias del backend..."
  # shellcheck disable=SC1091
  "$VENV_DIR/bin/python" -m pip install --upgrade pip wheel setuptools
  "$VENV_DIR/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
  ok "Dependencias backend instaladas"
}

# --- Frontend (npm) ----------------------------------------------------------
install_frontend_deps() {
  log "Instalando dependencias del frontend (npm install)..."
  (cd "$FRONTEND_DIR" && npm install --no-audit --no-fund)
  ok "Dependencias frontend instaladas"
}

# --- .env --------------------------------------------------------------------
ensure_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    ok ".env ya presente en $ENV_FILE"
    return
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  ok ".env creado a partir de .env.example"
}

# --- Main --------------------------------------------------------------------
main() {
  log "Iniciando setup de UPV-EARTH en $ROOT_DIR"
  detect_os
  ensure_brew
  ensure_python
  ensure_node
  ensure_ollama
  ensure_venv
  install_backend_deps
  install_frontend_deps
  ensure_env_file
  start_ollama_bg
  pull_model
  mkdir -p "$ROOT_DIR/.runtime/pids" "$ROOT_DIR/.runtime/logs"
  ok "Setup completado. Ahora arranca la app con:  ./launch.sh"
}

main "$@"
