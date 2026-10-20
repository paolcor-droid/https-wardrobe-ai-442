#!/usr/bin/env bash
# Idempotent, data-preserving LUMIÈRE Codespaces startup.
# NEVER creates/removes containers, volumes, databases, accounts or demo assets.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/.lumiere-dev-logs"
CONTAINER="lumiere-dev-mongo"
mkdir -p "$LOGS"
chmod 700 "$LOGS"

command -v flock >/dev/null || { echo "flock is required." >&2; exit 1; }
exec 9>"$LOGS/startup.lock"
flock -n 9 || { echo "Another LUMIÈRE startup is already running." >&2; exit 1; }

api_live() {
  [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8000/health/live 2>/dev/null || true)" == "200" ]]
}
api_ready() {
  [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8000/health/ready 2>/dev/null || true)" == "200" ]]
}
web_ready() {
  # A missing session returns 401 (or 200 if the browser is already signed in).
  # A 502 confirms that the Expo proxy cannot reach FastAPI.
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8081/api/account/me 2>/dev/null || true)"
  [[ "$code" == "401" || "$code" == "200" ]]
}
port_in_use() {
  python - "$1" <<'PY'
import socket, sys
port = int(sys.argv[1])
for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
    try:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((address, port)) == 0:
                sys.exit(0)
    except OSError:
        pass
sys.exit(1)
PY
}
wait_until() {
  local description="$1" count="$2" command="$3"
  for ((i=0; i<count; i++)); do
    if "$command"; then return 0; fi
    sleep 2
  done
  echo "Timed out waiting for $description." >&2
  return 1
}

echo "[1/5] Checking existing MongoDB container..."
command -v docker >/dev/null || { echo "Docker CLI is unavailable." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker daemon is unavailable." >&2; exit 1; }
docker container inspect "$CONTAINER" >/dev/null 2>&1 || {
  echo "Existing $CONTAINER not found. Refusing to create an empty replacement database." >&2
  exit 1
}
if [[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER")" != "true" ]]; then
  echo "Starting existing $CONTAINER (retaining its volumes)..."
  docker start "$CONTAINER" || { echo "Docker could not start $CONTAINER; inspect its runtime state, do not delete its volumes." >&2; exit 1; }
else
  echo "$CONTAINER is already running."
fi

mongo_ready() {
  docker exec "$CONTAINER" mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx '1'
}
echo "[2/5] Waiting for MongoDB..."
wait_until "MongoDB" 45 mongo_ready || { echo "Inspect: docker logs $CONTAINER" >&2; exit 1; }

# Fail safely rather than pointing the backend at the wrong DB.
[[ -f "$ROOT/backend/.env" ]] || { echo "backend/.env is missing; refusing to use an unconfigured database." >&2; exit 1; }
python - "$ROOT/backend/.env" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import dotenv_values
config = dotenv_values(Path(sys.argv[1]))
url = urlsplit(config.get("MONGO_URL") or "")
if url.scheme != "mongodb" or url.hostname not in ("127.0.0.1", "localhost") or url.port != 27017 or not config.get("DB_NAME"):
    raise SystemExit("Refusing startup: backend/.env must use the existing local MongoDB at 127.0.0.1:27017 with a configured DB_NAME.")
PY

echo "[3/5] Checking FastAPI on port 8000..."
if api_ready; then
  echo "Healthy FastAPI already running; reusing it."
elif port_in_use 8000; then
  echo "Port 8000 is occupied but /health/ready is unhealthy. Inspect the existing process; no automatic kill." >&2
  exit 1
else
  (
    cd "$ROOT/backend"
    nohup python -m uvicorn server:app --host 0.0.0.0 --port 8000 >"$LOGS/backend.log" 2>&1 </dev/null &
    echo $! >"$LOGS/backend.pid"
  )
  wait_until "FastAPI readiness (see $LOGS/backend.log)" 45 api_ready || exit 1
fi
api_live || { echo "FastAPI liveness failed." >&2; exit 1; }

echo "[4/5] Checking Expo web on port 8081..."
if web_ready; then
  echo "Healthy Expo/API proxy already running; reusing it."
elif port_in_use 8081; then
  echo "Port 8081 is occupied. Waiting for the existing Expo server to become healthy..."
  wait_until "existing Expo/API proxy" 15 web_ready || {
    echo "Port 8081 still does not proxy to FastAPI. Inspect the existing Expo terminal; no automatic kill." >&2
    exit 1
  }
else
  [[ -x "$ROOT/frontend/node_modules/.bin/expo" ]] || {
    echo "Expo dependencies are missing; run 'cd frontend && npm install' first." >&2
    exit 1
  }
  (
    cd "$ROOT/frontend"
    nohup ./node_modules/.bin/expo start --web --port 8081 --host localhost >"$LOGS/frontend.log" 2>&1 </dev/null &
    echo $! >"$LOGS/frontend.pid"
  )
  wait_until "Expo/API proxy (see $LOGS/frontend.log)" 60 web_ready || exit 1
fi

echo "[5/5] Final checks..."
mongo_ready && api_live && api_ready && web_ready || {
  echo "One or more health checks failed; inspect $LOGS." >&2
  exit 1
}
echo "READY: existing MongoDB, FastAPI :8000 and Expo web :8081."
echo "Open the forwarded PRIVATE Codespaces port 8081."
echo "Logs for processes started here: $LOGS"
echo "After a Codespace restart, rerun: bash scripts/start-lumiere-dev.sh"
