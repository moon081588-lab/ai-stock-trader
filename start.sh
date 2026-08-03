#!/usr/bin/env bash
#
# Start everything: API + dashboard. Ctrl+C stops both.
#
#   ./start.sh
#
# First run also creates the virtualenv and installs dependencies, so this is
# the only command needed on a fresh clone.
set -euo pipefail

cd "$(dirname "$0")"

API_PORT=8000
WEB_PORT=5173

# --- one-time setup -----------------------------------------------------------

if [ ! -d .venv ]; then
  echo "→ creating virtualenv"
  python3 -m venv .venv
fi

# Cheap check: if uvicorn is missing, dependencies were never installed (or the
# venv predates a requirements change).
if [ ! -x .venv/bin/uvicorn ]; then
  echo "→ installing Python dependencies"
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "→ installing frontend dependencies"
  (cd frontend && npm install --no-audit --no-fund)
fi

# --- port check ---------------------------------------------------------------

for port in "$API_PORT" "$WEB_PORT"; do
  if lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✗ port $port is already in use — is another copy running?"
    echo "  free it with:  lsof -ti :$port | xargs kill"
    exit 1
  fi
done

# --- run ----------------------------------------------------------------------

# Kill the whole process group on exit so Ctrl+C doesn't orphan a server.
trap 'kill 0 2>/dev/null || true' EXIT INT TERM

# --reload-dir app matters: plain --reload also watches .venv, and site-packages
# churn restarts the server every few seconds, which drops the price stream and
# re-fetches every symbol until Yahoo rate-limits you.
#
# PYTHONWARNINGS hides yfinance's DeprecationWarning spam on Python 3.14. Drop
# it if you're debugging warnings in our own code.
PYTHONWARNINGS="ignore::DeprecationWarning" \
  ./.venv/bin/uvicorn app.main:app \
    --reload --reload-dir app --port "$API_PORT" 2>&1 |
  sed -u 's/^/[api] /' &

(cd frontend && npm run dev -- --port "$WEB_PORT") 2>&1 |
  sed -u 's/^/[web] /' &

echo
echo "  dashboard  http://localhost:$WEB_PORT"
echo "  api docs   http://127.0.0.1:$API_PORT/docs"
echo "  Ctrl+C to stop both"
echo

# Open the dashboard once Vite is actually listening. Terminal.app needs a
# ⌘-click to follow a printed URL, which is a poor greeting for a dev server.
# Set NO_OPEN=1 to skip.
open_when_ready() {
  for _ in $(seq 1 60); do
    if lsof -i ":$WEB_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
      open "http://localhost:$WEB_PORT"
      return
    fi
    sleep 0.25
  done
  echo "[web] didn't come up within 15s — open http://localhost:$WEB_PORT yourself"
}

if [ "${NO_OPEN:-}" != "1" ] && command -v open >/dev/null 2>&1; then
  open_when_ready &
fi

wait
