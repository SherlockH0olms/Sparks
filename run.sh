#!/usr/bin/env bash
# AEGIS LOOP — tek komutla başlat (backend + frontend)
set -e
cd "$(dirname "$0")"

PY=""
for c in "../.venv/bin/python" "./.venv/bin/python" "python3"; do
  if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then PY="$c"; break; fi
done
[ -z "$PY" ] && { echo "python bulunamadı"; exit 1; }

echo "==> Backend bağımlılıkları kontrol ediliyor"
"$PY" -c "import fastapi, uvicorn, pydantic" 2>/dev/null || "$PY" -m pip install -q -r backend/requirements.txt

echo "==> Backend başlatılıyor (http://127.0.0.1:8000)"
(cd backend && PYTHONPATH=. "$PY" -m uvicorn aegis.api:app --host 127.0.0.1 --port 8000) &
BACK_PID=$!
trap 'kill $BACK_PID 2>/dev/null' EXIT

# API hazır olana dek bekle
for i in $(seq 1 30); do
  curl -s -m 1 http://127.0.0.1:8000/api/health >/dev/null 2>&1 && break
  sleep 1
done
echo "==> API hazır"

echo "==> Frontend başlatılıyor (http://localhost:3000)"
cd frontend
[ -d node_modules ] || npm install --no-audit --no-fund
exec npm run dev
