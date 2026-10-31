#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm ci)
fi
exec .venv/bin/python scripts/run.py "$@"
