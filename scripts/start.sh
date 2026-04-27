#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-6002}"

exec uvicorn backend.main:app --host "$HOST" --port "$PORT"
