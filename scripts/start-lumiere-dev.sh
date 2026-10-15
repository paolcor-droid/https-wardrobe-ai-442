#!/usr/bin/env bash
# Start the PRIVATE LUMIÈRE Codespaces preview without resetting data.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null || ! docker info >/dev/null 2>&1; then
  echo "Docker is required for the existing private MongoDB container." >&2
  exit 1
fi
if ! docker container inspect lumiere-dev-mongo >/dev/null 2>&1; then
  echo "Existing lumiere-dev-mongo container not found; refusing to create a new empty database." >&2
  exit 1
fi
docker start lumiere-dev-mongo >/dev/null
echo "Checking existing MongoDB (no database reset)..."
ready=0
for _ in $(seq 1 30); do
  if docker exec lumiere-dev-mongo mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx 1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" != 1 ]; then
  echo "MongoDB did not become healthy. Inspect: docker logs lumiere-dev-mongo" >&2
  exit 1
fi
if ss -ltn 2>/dev/null | grep -Eq ':[[:space:]]*8000[[:space:]]'; then
  echo "Port 8000 is occupied. Stop the old FastAPI process manually before restarting." >&2
  exit 1
fi
if ss -ltn 2>/dev/null | grep -Eq ':[[:space:]]*8081[[:space:]]'; then
  echo "Port 8081 is occupied. Stop the old Expo process manually before restarting." >&2
  exit 1
fi
mkdir -p "$ROOT/.lumiere-dev-logs"
cleanup() {
  trap - EXIT INT TERM
  [ -z "${api_pid:-}" ] || kill "$api_pid" 2>/dev/null || true
  [ -z "${web_pid:-}" ] || kill "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
(
  cd "$ROOT/backend"
  exec python -m uvicorn server:app --host 0.0.0.0 --port 8000
) > "$ROOT/.lumiere-dev-logs/backend.log" 2>&1 &
api_pid=$!
for _ in $(seq 1 30); do
  if ! kill -0 "$api_pid" 2>/dev/null; then
    echo "Backend exited. See .lumiere-dev-logs/backend.log" >&2
    exit 1
  fi
  if ss -ltn 2>/dev/null | grep -Eq ':8000[[:space:]]'; then break; fi
  sleep 1
done
if ! ss -ltn 2>/dev/null | grep -Eq ':8000[[:space:]]'; then
  echo "Backend did not start. See .lumiere-dev-logs/backend.log" >&2
  exit 1
fi
(
  cd "$ROOT/frontend"
  exec npx expo start --web --host lan
) > "$ROOT/.lumiere-dev-logs/frontend.log" 2>&1 &
web_pid=$!
echo "Private development preview starting on Codespaces port 8081."
echo "Logs: .lumiere-dev-logs/backend.log and frontend.log"
echo "Use Codespaces Ports → 8081. Keep this terminal running; Ctrl+C stops these two processes."
wait "$web_pid"
