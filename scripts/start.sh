#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"

if [ -d "$VENV_DIR" ]; then
  source "$VENV_DIR/bin/activate"
fi

export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"
exec python -m uvicorn jez_face_api.app:create_app --factory --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"

