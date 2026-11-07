#!/usr/bin/env bash
# Start the demo server (port 8000) and web app (port 3000) together. Ctrl+C stops both.
# Usage: scripts/dev.sh            # development mode
#        scripts/dev.sh --prod     # production build of the web app (use on demo night)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -f "$ROOT/server/.env" ]]; then
  set -a; source "$ROOT/server/.env"; set +a
fi
# ELEVENLABS_API_KEY, written here by `npx @elevenlabs/cli onboard` (ADR-009 listening test).
if [[ -f "$ROOT/.env.local" ]]; then
  set -a; source "$ROOT/.env.local"; set +a
fi

( cd "$ROOT/server" && uv run uvicorn main:create_app --factory --host 0.0.0.0 --port 8000 ) &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# The laptop's address on the local network, for the TV (macOS first, then Linux).
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true)"
echo
echo "  Physician controller (this laptop):  http://localhost:3000/control"
if [[ -n "$LAN_IP" ]]; then
  echo "  Shared screen (TV on the same Wi-Fi): http://$LAN_IP:3000/screen"
else
  echo "  Shared screen (TV on the same Wi-Fi): http://<this laptop's IP>:3000/screen"
fi
echo

cd "$ROOT/web"
if [[ "${1:-}" == "--prod" ]]; then
  npm run build && npm run start -- --hostname 0.0.0.0 --port 3000
else
  npm run dev -- --hostname 0.0.0.0 --port 3000
fi
