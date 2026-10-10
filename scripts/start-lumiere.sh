#!/usr/bin/env bash
# Start the local LUMIÈRE Codespaces preview without resetting its data.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/.lumiere-dev-logs"
mkdir -p "$LOG_DIR"

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable. Start Docker in Codespaces and retry." >&2
  exit 1
fi

if docker container inspect lumiere-mongodb >/dev/null 2>&1; then
  if [[ "$(docker inspect -f '{{.State.Running}}' lumiere-mongodb)" != "true" ]]; then
    echo "Starting existing MongoDB container..."
    if ! docker start lumiere-mongodb; then
      echo "MongoDB container could not start. Do not delete the lumiere-mongo-data volume." >&2
      echo "The container may need to be recreated using that volume." >&2
      exit 1
    fi
  else
    echo "MongoDB container already running."
  fi
else
  if ! docker volume inspect lumiere-mongo-data >/dev/null 2>&1; then
    echo "Creating MongoDB persistent volume..."
    docker volume create lumiere-mongo-data >/dev/null
  fi
  echo "Creating MongoDB container using the persistent volume..."
  docker run -d --name lumiere-mongodb -p 127.0.0.1:27017:27017 \
    -v lumiere-mongo-data:/data/db mongo:7 >/dev/null
fi

echo "Waiting for MongoDB..."
mongo_ready=false
for _ in $(seq 1 30); do
  if docker exec lumiere-mongodb mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx 1; then
    mongo_ready=true
    break
  fi
  sleep 2
done
if [[ "$mongo_ready" != true ]]; then
  echo "MongoDB did not become ready. Check: docker logs lumiere-mongodb" >&2
  exit 1
fi

if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  echo "Missing backend/.venv. Set up the backend Python environment first." >&2
  exit 1
fi
if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "Missing backend/.env (local MongoDB configuration). Set it up before starting." >&2
  exit 1
fi
if [[ ! -x "$ROOT/frontend/node_modules/.bin/expo" ]]; then
  echo "Missing Expo dependencies. Install frontend dependencies first." >&2
  exit 1
fi

if curl -fsS --max-time 2 http://127.0.0.1:8000/api/profile >/dev/null 2>&1; then
  echo "FastAPI already running."
else
  echo "Starting FastAPI..."
  (cd "$ROOT" && nohup env PYTHONPATH=backend backend/.venv/bin/python -m uvicorn server:app \
    --app-dir backend --host 0.0.0.0 --port 8000 >"$LOG_DIR/backend.log" 2>&1 </dev/null &)
  backend_ready=false
  for _ in $(seq 1 20); do
    if curl -fsS --max-time 2 http://127.0.0.1:8000/api/profile >/dev/null 2>&1; then
      backend_ready=true
      break
    fi
    sleep 1
  done
  if [[ "$backend_ready" != true ]]; then
    echo "FastAPI did not become ready. See $LOG_DIR/backend.log" >&2
    exit 1
  fi
fi

# Expo started with --host localhost can listen on IPv6 (::1), not 127.0.0.1.
# Verify the actual web API before deciding whether another Expo process is needed.
expo_responding() {
  curl -fsS --max-time 5 http://localhost:8081/api/profile >/dev/null 2>&1
}

port_occupied() {
  "$ROOT/backend/.venv/bin/python" -c 'import socket; ports=[(socket.AF_INET,"127.0.0.1"),(socket.AF_INET6,"::1")]; found=False
for family,host in ports:
 try:
  with socket.socket(family,socket.SOCK_STREAM) as sock:
   sock.settimeout(2)
   if sock.connect_ex((host,8081)) == 0: found=True
 except OSError: pass
raise SystemExit(0 if found else 1)'
}

if expo_responding; then
  echo "Expo web proxy already running."
elif port_occupied; then
  echo "Port 8081 is occupied, but the LUMIÈRE API proxy is not responding yet."
  echo "Waiting for the existing server instead of launching a duplicate..."
else
  echo "Starting Expo web preview on port 8081..."
  (cd "$ROOT/frontend" && nohup ./node_modules/.bin/expo start --web --host localhost --port 8081 \
    >"$LOG_DIR/expo.log" 2>&1 </dev/null &)
fi

echo "Checking the LUMIÈRE web proxy..."
expo_ready=false
for _ in $(seq 1 90); do
  if expo_responding; then
    expo_ready=true
    break
  fi
  sleep 2
done
if [[ "$expo_ready" != true ]]; then
  echo "Port 8081 did not serve the expected LUMIÈRE API proxy." >&2
  echo "Check the existing Expo terminal or $LOG_DIR/expo.log." >&2
  echo "The script will not change ports or stop an existing process automatically." >&2
  exit 1
fi

echo
echo "LUMIÈRE local preview is ready."
echo "Open the forwarded Codespaces port 8081 (web app)."
echo "Backend API is on local port 8000; MongoDB is bound to localhost only."
echo "Logs (for services started by this script): $LOG_DIR"
