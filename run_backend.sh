#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${ROOT_DIR}/.venv/bin/python" -m uvicorn \
  backend.main:app \
  --app-dir "${ROOT_DIR}" \
  --host 127.0.0.1 \
  --port 8001 \
  "$@"