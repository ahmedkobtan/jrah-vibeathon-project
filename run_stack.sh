#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend/widget"
BACKEND_REQUIREMENTS="${BACKEND_DIR}/requirements.txt"

PYTHON_BIN="${TRANSPARENTCARE_PYTHON_BIN:-python3}"
BACKEND_VENV="${TRANSPARENTCARE_BACKEND_VENV:-${BACKEND_DIR}/.venv}"
BACKEND_PORT="${TRANSPARENTCARE_BACKEND_PORT:-8000}"
FRONTEND_PORT="${TRANSPARENTCARE_WIDGET_PORT:-5173}"
BACKEND_HOST="${TRANSPARENTCARE_BACKEND_HOST:-0.0.0.0}"
FRONTEND_HOST="${TRANSPARENTCARE_WIDGET_HOST:-0.0.0.0}"
FRONTEND_ARGS=("--host" "${FRONTEND_HOST}")
BACKEND_PIP="${BACKEND_VENV}/bin/pip"
BACKEND_UVICORN="${BACKEND_VENV}/bin/uvicorn"
BACKEND_REQUIREMENTS_STAMP="${BACKEND_VENV}/.requirements-installed"

cleanup() {
  local exit_code=$?
  if [[ -n "${BACKEND_PID:-}" ]] && ps -p "${BACKEND_PID}" > /dev/null 2>&1; then
    echo "Stopping backend (PID ${BACKEND_PID})"
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]] && ps -p "${FRONTEND_PID}" > /dev/null 2>&1; then
    echo "Stopping frontend (PID ${FRONTEND_PID})"
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
    wait "${FRONTEND_PID}" 2>/dev/null || true
  fi

  exit "${exit_code}"
}

trap cleanup INT TERM EXIT

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Error: Python interpreter '${PYTHON_BIN}' not found on PATH." >&2
  exit 1
fi

if [[ ! -d "${BACKEND_VENV}" ]]; then
  echo "Creating backend virtual environment at ${BACKEND_VENV}..."
  "${PYTHON_BIN}" -m venv "${BACKEND_VENV}"
fi

if [[ -f "${BACKEND_REQUIREMENTS}" ]]; then
  if [[ ! -x "${BACKEND_PIP}" ]]; then
    echo "Error: pip not found in virtual environment ${BACKEND_VENV}." >&2
    exit 1
  fi

  if [[ ! -f "${BACKEND_REQUIREMENTS_STAMP}" || "${BACKEND_REQUIREMENTS}" -nt "${BACKEND_REQUIREMENTS_STAMP}" ]]; then
    echo "Installing backend Python dependencies..."
    "${BACKEND_PIP}" install --upgrade pip >/dev/null
    "${BACKEND_PIP}" install -r "${BACKEND_REQUIREMENTS}"
    touch "${BACKEND_REQUIREMENTS_STAMP}"
  fi
fi

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "${FRONTEND_DIR}" && npm install)
fi

echo "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}..."
(
  cd "${PROJECT_ROOT}"
  "${BACKEND_UVICORN}" backend.app.main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) &
BACKEND_PID=$!

sleep 1

echo "Starting frontend dev server on port ${FRONTEND_PORT}..."
(
  cd "${FRONTEND_DIR}"
  npm run dev -- --port "${FRONTEND_PORT}" "${FRONTEND_ARGS[@]}"
) &
FRONTEND_PID=$!

echo ""
echo "Backend:    http://localhost:${BACKEND_PORT}/docs"
echo "Frontend:   http://localhost:${FRONTEND_PORT}/"
echo "Press Ctrl+C to stop both."

wait

