#!/usr/bin/env bash
# LUMIÈRE private Codespaces development startup. Never exposes database/API ports.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.lumiere-dev"
mkdir -p "$RUNTIME"
chmod 700 "$RUNTIME"
container="lumiere-test-mongo-2"
echo "LUMIÈRE development services"
if ! docker inspect "$container" >/dev/null 2>&1; then
  echo "ERROR: $container is missing. Refusing to create or erase a database automatically." >&2
  exit 1
fi
if [[ "$(docker inspect -f '{{.State.Running}}' "$container")" != "true" ]]; then
  echo "Starting existing MongoDB container..."
  if ! docker start "$container"; then
    echo "ERROR: Docker runtime could not start $container. Try stopping and restarting the Codespace; do not delete the database." >&2
    exit 1
  fi
fi
echo "Waiting for MongoDB ..."
for i in {1..30}; do
  if docker exec "$container" mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx '1'; then break; fi
  sleep 1
done
if ! docker exec "$container" mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx '1'; then
  echo "ERROR: MongoDB did not respond. Inspect docker logs $container." >&2; exit 1
fi
probe() { curl -fsS --max-time 3 -o /dev/null "http://127.0.0.1:$1/" 2>/dev/null; }
account_probe() {
  [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://127.0.0.1:8000/api/account/me 2>/dev/null)" == "401" ]]
}
if ! account_probe; then
  if command -v fuser >/dev/null && fuser -n tcp 8000 >/dev/null 2>&1; then
    echo "ERROR: Port 8000 is in use but account API is unhealthy; refusing to kill an unknown process." >&2; exit 1
  fi
  echo "Starting FastAPI..."
  ( cd "$ROOT/backend"
    export MONGO_URL=mongodb://127.0.0.1:27018 DB_NAME=lumiere_security_test_2
    export LUMIERE_LOCAL_IMAGE_STORAGE=1 LUMIERE_WEB_COOKIE_SECURE=1
    export LUMIERE_PUBLIC_DEPLOYMENT=0 ENVIRONMENT=development
    nohup python -m uvicorn server:app --host 127.0.0.1 --port 8000 > "$RUNTIME/fastapi.log" 2>&1 < /dev/null & echo $! > "$RUNTIME/fastapi.pid"
  )
fi
for i in {1..35}; do account_probe && break; sleep 1; done
if ! account_probe; then echo "ERROR: FastAPI failed. See $RUNTIME/fastapi.log" >&2; exit 1; fi
if ! probe 8081; then
  if command -v fuser >/dev/null && fuser -n tcp 8081 >/dev/null 2>&1; then
    echo "ERROR: 8081 is occupied but the web server is unhealthy." >&2; exit 1
  fi
  echo "Starting Expo web..."
  ( cd "$ROOT/frontend"
    nohup npx expo start --web --port 8081 > "$RUNTIME/expo.log" 2>&1 < /dev/null & echo $! > "$RUNTIME/expo.pid"
  )
fi
for i in {1..65}; do probe 8081 && break; sleep 2; done
if ! probe 8081; then echo "ERROR: Expo failed. See $RUNTIME/expo.log" >&2; exit 1; fi
echo "READY: MongoDB (27018), FastAPI (8000 /api/account/me => 401), Expo (8081 => 200)."
echo "Open the PRIVATE port 8081 from Codespaces Ports tab."
echo "Logs: $RUNTIME/fastapi.log and $RUNTIME/expo.log"
echo "Services may stop when Codespaces stops; rerun this script after restart."
