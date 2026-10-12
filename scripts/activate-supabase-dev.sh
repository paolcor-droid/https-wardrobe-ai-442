#!/usr/bin/env bash
# Opt-in development-only switch for new LUMIÈRE photos to private Supabase.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$ROOT/.lumiere-dev/fastapi.pid"
LOG="$ROOT/.lumiere-dev/fastapi.log"
: "${LUMIERE_SUPABASE_SERVICE_ROLE_KEY:?Codespaces secret unavailable}"
[[ "${LUMIERE_SUPABASE_SWITCH_ACK:-}" == "switch-new-photos-only" ]] || { echo "Set LUMIERE_SUPABASE_SWITCH_ACK=switch-new-photos-only"; exit 1; }
[[ -f "$PIDFILE" ]] || { echo "No managed FastAPI PID found; refusing to interrupt unknown server"; exit 1; }
PID="$(cat "$PIDFILE")"
[[ "$PID" =~ ^[0-9]+$ ]] || { echo "Invalid managed PID"; exit 1; }
[[ -r "/proc/$PID/cmdline" ]] || { echo "Managed FastAPI process not running; refusing"; exit 1; }
CMD="$(tr '\0' ' ' </proc/"$PID"/cmdline)"
[[ "$CMD" == *"uvicorn server:app"* && "$CMD" == *"--port 8000"* ]] || { echo "Port 8000 process does not match managed FastAPI; refusing"; exit 1; }
export LUMIERE_SUPABASE_URL="https://sicszettmpnyniyhbhsl.supabase.co"
export LUMIERE_SUPABASE_BUCKET="lumiere-private-photos"
export LUMIERE_PHOTO_STORAGE="supabase"
export LUMIERE_LOCAL_IMAGE_STORAGE="1"
export MONGO_URL="mongodb://127.0.0.1:27018" DB_NAME="lumiere_security_test_2"
export LUMIERE_PUBLIC_DEPLOYMENT="0" LUMIERE_WEB_COOKIE_SECURE="1" ENVIRONMENT="development"
PYTHONPATH="$ROOT/backend" python - <<'PY'
from services.supabase_photos import verify_private_bucket
assert verify_private_bucket()
print("PASS: intended Supabase bucket is private")
PY
echo "Restarting only the managed development FastAPI process. Local photo directory and MongoDB are preserved."
kill "$PID"
for i in {1..25}; do
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  sleep .2
done
if kill -0 "$PID" 2>/dev/null; then
  echo "Managed FastAPI did not stop. Refusing to start a duplicate." >&2
  exit 1
fi
(
  cd "$ROOT/backend"
  nohup python -m uvicorn server:app --host 127.0.0.1 --port 8000 > "$LOG" 2>&1 < /dev/null &
  echo $! > "$PIDFILE"
)
for i in {1..40}; do
  STATUS="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8000/api/account/me 2>/dev/null || true)"
  if [[ "$STATUS" == 401 ]]; then
    echo "PASS: private development FastAPI running with Supabase for NEW photographs"
    echo "Existing local photo files and MongoDB records were not modified."
    exit 0
  fi
  sleep 1
done
echo "ERROR: FastAPI did not become ready. Check $LOG" >&2
exit 1
