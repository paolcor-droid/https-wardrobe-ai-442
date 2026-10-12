#!/usr/bin/env bash
# Private Codespaces development: activate Resend SMTP and retain Supabase new-photo storage.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$ROOT/.lumiere-dev/fastapi.pid"
LOG="$ROOT/.lumiere-dev/fastapi.log"
[[ "${LUMIERE_RESEND_SMTP_ACK:-}" == "enable-test-recovery" ]] || { echo "Explicit test acknowledgement required"; exit 1; }
: "${LUMIERE_RESEND_API_KEY:?Missing Codespaces Resend secret}"
: "${LUMIERE_SUPABASE_SERVICE_ROLE_KEY:?Missing Codespaces Supabase secret}"
[[ -f "$PIDFILE" ]] || { echo "Managed FastAPI PID not found"; exit 1; }
PID="$(cat "$PIDFILE")"
[[ "$PID" =~ ^[0-9]+$ ]] || exit 1
[[ -r "/proc/$PID/cmdline" ]] || { echo "Managed FastAPI not running"; exit 1; }
CMD="$(tr '\0' ' ' <"/proc/$PID/cmdline")"
[[ "$CMD" == *"uvicorn server:app"* && "$CMD" == *"--port 8000"* ]] || { echo "Refusing to stop unknown process"; exit 1; }
export LUMIERE_SUPABASE_URL=https://sicszettmpnyniyhbhsl.supabase.co
export LUMIERE_SUPABASE_BUCKET=lumiere-private-photos
export LUMIERE_PHOTO_STORAGE=supabase LUMIERE_LOCAL_IMAGE_STORAGE=1
export LUMIERE_SMTP_HOST=smtp.resend.com LUMIERE_SMTP_PORT=587 LUMIERE_SMTP_USER=resend
export LUMIERE_SMTP_PASSWORD="$LUMIERE_RESEND_API_KEY"
export LUMIERE_RECOVERY_FROM=onboarding@resend.dev
export LUMIERE_RECOVERY_BASE_URL=https://potential-fortnight-97g7r4gj46x7h97jg-8081.app.github.dev
export MONGO_URL=mongodb://127.0.0.1:27018 DB_NAME=lumiere_security_test_2
export LUMIERE_PUBLIC_DEPLOYMENT=0 LUMIERE_WEB_COOKIE_SECURE=1 ENVIRONMENT=development
PYTHONPATH="$ROOT/backend" python - <<'PY'
from services.supabase_photos import verify_private_bucket
from services.account_recovery import recovery_configured
assert verify_private_bucket()
assert recovery_configured()
print("PASS: private Supabase bucket and Resend SMTP recovery configuration validated")
PY
echo "Restarting managed private FastAPI only; MongoDB, photos, and Expo unchanged."
kill "$PID"
for i in {1..40}; do
  kill -0 "$PID" 2>/dev/null || break
  sleep .2
done
if kill -0 "$PID" 2>/dev/null; then
  echo "Managed FastAPI failed to stop. Refusing duplicate." >&2
  exit 1
fi
(
  cd "$ROOT/backend"
  nohup python -m uvicorn server:app --host 127.0.0.1 --port 8000 > "$LOG" 2>&1 < /dev/null &
  echo $! > "$PIDFILE"
)
for i in {1..40}; do
  STATUS="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8000/api/account/me 2>/dev/null || true)"
  if [[ "$STATUS" == "401" ]]; then
    echo "PASS: FastAPI running with private Supabase storage and Resend test SMTP settings"
    echo "No recovery message has been sent yet. Sender is restricted to Resend-approved test recipients."
    exit 0
  fi
  sleep 1
done
echo "ERROR: API not ready; check private log $LOG" >&2
exit 1
