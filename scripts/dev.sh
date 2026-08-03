#!/usr/bin/env bash
# Start the API for local development.
#
# --reload-dir app is the important part. Plain `--reload` watches the whole
# project including .venv/, and site-packages churns constantly on macOS. That
# restarted the server every few seconds, which tore down the Yahoo WebSocket,
# wiped the in-memory board cache, and triggered a fresh 24-symbol fetch each
# time — enough request volume to get the IP rate-limited within minutes.
set -euo pipefail

cd "$(dirname "$0")/.."

exec uvicorn app.main:app \
  --reload \
  --reload-dir app \
  --port 8000
