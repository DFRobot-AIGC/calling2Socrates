#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-}"
OLLAMA_MODEL_DEFAULT="qwen3.5:2b"

log() {
  printf '[deploy] %s\n' "$1"
}

warn() {
  printf '[deploy] warning: %s\n' "$1" >&2
}

fail() {
  printf '[deploy] error: %s\n' "$1" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "missing required command: $1"
  fi
}

resolve_python_bin() {
  if [[ -n "${PYTHON_BIN}" ]]; then
    command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "requested Python interpreter not found: ${PYTHON_BIN}"
    printf '%s\n' "${PYTHON_BIN}"
    return
  fi

  for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return
    fi
  done

  fail "no supported Python interpreter found; set PYTHON_BIN explicitly"
}

ensure_env_file() {
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    log ".env already exists, keeping current values"
    return
  fi

  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
  log "created .env from .env.example"
}

read_ollama_model() {
  local model

  if [[ -f "${ROOT_DIR}/.env" ]]; then
    model="$(grep -E '^OLLAMA_MODEL=' "${ROOT_DIR}/.env" | tail -n 1 | cut -d= -f2- || true)"
  else
    model=""
  fi

  if [[ -z "${model}" ]]; then
    model="${OLLAMA_MODEL_DEFAULT}"
  fi

  printf '%s\n' "${model}"
}

setup_uv_venv() {
  local python_bin

  require_cmd uv
  python_bin="$(resolve_python_bin)"

  if [[ ! -d "${VENV_DIR}" ]]; then
    log "creating uv virtual environment at ${VENV_DIR}"
    uv venv "${VENV_DIR}" --python "${python_bin}"
  else
    log "using existing virtual environment at ${VENV_DIR}"
  fi

  log "installing Python dependencies with uv"
  uv pip install --python "${VENV_DIR}/bin/python" -r "${ROOT_DIR}/requirements.txt"
}

pull_ollama_model() {
  local model
  model="$(read_ollama_model)"

  if [[ "${SKIP_OLLAMA_PULL:-0}" == "1" ]]; then
    log "SKIP_OLLAMA_PULL=1, skipping Ollama model pull"
    return
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    warn "ollama is not installed, skipped pulling model ${model}"
    return
  fi

  log "pulling Ollama model ${model}"
  ollama pull "${model}"
}

print_next_steps() {
  cat <<EOF

Deployment complete.

Next steps:
  1. Edit ${ROOT_DIR}/.env if you need custom MQTT, DeepSeek, or audio settings.
  2. Activate the environment: source ${VENV_DIR}/bin/activate
  3. Start the host app: python ${ROOT_DIR}/chat.py

Notes:
  - This script deploys the computer-side app only.
  - Upload ${ROOT_DIR}/main.py to the UNIHIKER separately if you are using the board.
EOF
}

main() {
  require_cmd cp
  require_cmd grep

  ensure_env_file
  setup_uv_venv
  pull_ollama_model
  print_next_steps
}

main "$@"
