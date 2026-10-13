#!/usr/bin/env bash
# Starts ONLY a localhost private account API against isolated disposable Mongo.
# No Tailscale Serve/Funnel or GitHub port publishing.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ "${CODESPACE_NAME:-}" == "solid-space-waffle-g4v4jwv7wr7gh9r7v" ]] || { echo "BLOCKED: wrong Codespace" >&2; exit 2; }
[[ "$(git branch --show-current)" == "lumiere-recommendations-v2" ]] || { echo "BLOCKED: wrong branch" >&2; exit 2; }
[[ "$(docker inspect -f '{{.State.Running}}' lumiere-android-staging-mongo 2>/dev/null)" == "true" ]] || { echo "BLOCKED: staging MongoDB not running" >&2; exit 2; }
docker exec lumiere-android-staging-mongo mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' | grep -qx 1 || { echo "BLOCKED: database unhealthy" >&2; exit 2; }
runtime="$ROOT/.lumiere-android-staging"
mkdir -p "$runtime"; chmod 700 "$runtime"
pidfile="$runtime/api.pid"
if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
  echo "Existing staging API PID $(cat "$pidfile"); refusing to launch a duplicate."
  exit 2
fi
if [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8015/api/account/me || true)" != "000" ]]; then
  echo "BLOCKED: port 8015 already responds; refusing to replace an unknown API." >&2; exit 2
fi
(
  cd "$ROOT/backend"
  export MONGO_URL="mongodb://127.0.0.1:27019"
  export DB_NAME="lumiere_android_staging_disposable"
  export LUMIERE_PUBLIC_DEPLOYMENT=0
  export LUMIERE_DISTRIBUTED_RATE_LIMIT=1
  export ENVIRONMENT=development
  export LUMIERE_LOCAL_IMAGE_STORAGE=1
  export LUMIERE_PHOTO_STORAGE=local
  export LUMIERE_WEB_COOKIE_SECURE=1
  # No production photo bucket, no outbound recovery mail in this initial test.
  unset LUMIERE_SUPABASE_SERVICE_ROLE_KEY LUMIERE_RESEND_API_KEY LUMIERE_SMTP_PASSWORD
  nohup python -m uvicorn server:app --host 127.0.0.1 --port 8015 > "$runtime/api.log" 2>&1 </dev/null &
  echo $! > "$pidfile"
)
for i in {1..30}; do
  status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8015/api/account/me || true)"
  if [[ "$status" == "401" ]]; then
    echo "PASS: staging account API running locally on 127.0.0.1:8015 (unauthenticated => 401)"
    echo "Database: lumiere_android_staging_disposable. Photos: staging local only."
    echo "Tailscale Serve NOT enabled. API is NOT publicly exposed by this script."
    exit 0
  fi
  if ! kill -0 "$(cat "$pidfile")" 2>/dev/null; then break; fi
  sleep 1
done
echo "ERROR: API not ready; inspect $runtime/api.log. No other environment was touched." >&2
exit 1
