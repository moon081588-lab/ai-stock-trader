#!/usr/bin/env bash
#
# Start the API and the dashboard. Ctrl+C stops both.
#
#   ./start.sh
#
# First run also creates the virtualenv and installs dependencies.
set -euo pipefail

cd "$(dirname "$0")"

API_PORT=8000
WEB_PORT=5173

# --- one-time setup -----------------------------------------------------------

if [ ! -d .venv ]; then
  echo "creating virtualenv"
  python3 -m venv .venv
fi

if [ ! -x .venv/bin/uvicorn ]; then
  echo "installing Python dependencies"
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "installing frontend dependencies"
  (cd frontend && npm install --no-audit --no-fund)
fi

# --- port check ---------------------------------------------------------------

for port in "$API_PORT" "$WEB_PORT"; do
  if lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "port $port is already in use. free it with:  lsof -ti :$port | xargs kill"
    exit 1
  fi
done

# --- run ----------------------------------------------------------------------

# Both servers are started directly rather than through a wrapper, so $! is the
# real process and we can stop it by PID. An earlier version used `kill 0` to
# take down the whole process group; that works, but killing a process group is
# also a common malware shape and not worth the ambiguity.
#
# --reload-dir app matters: plain --reload also watches .venv, and site-packages
# churn restarts the server every few seconds, which drops the price stream and
# refetches every symbol until Yahoo rate-limits you.
./.venv/bin/uvicorn app.main:app --reload --reload-dir app --port "$API_PORT" &
API_PID=$!

# exec replaces the subshell with vite itself, so WEB_PID is vite and not an npm
# wrapper that would orphan it on exit.
(cd frontend && exec node_modules/.bin/vite --port "$WEB_PORT") &
WEB_PID=$!

stop() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap stop EXIT INT TERM

echo
echo "  dashboard  http://localhost:$WEB_PORT"
echo "  api docs   http://127.0.0.1:$API_PORT/docs"
echo "  Ctrl+C to stop both"
echo

wait
