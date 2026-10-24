#!/usr/bin/env bash
# Start the demo server (port 8000) and web app (port 3000) together. Ctrl+C stops both.
# Usage: scripts/dev.sh            # development mode
#        scripts/dev.sh --prod     # production build of the web app (use on demo night)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -f "$ROOT/server/.env" ]]; then
  set -a; source "$ROOT/server/.env"; set +a
fi

( cd "$ROOT/server" && uv run uvicorn main:app --host 0.0.0.0 --port 8000 ) &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

cd "$ROOT/web"
if [[ "${1:-}" == "--prod" ]]; then
  npm run build && npm run start -- --hostname 0.0.0.0 --port 3000
else
  npm run dev -- --hostname 0.0.0.0 --port 3000
fi
