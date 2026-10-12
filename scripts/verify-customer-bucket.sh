#!/usr/bin/env bash
# Read-only preflight for LUMIÈRE intended customer Supabase bucket.
set -Eeuo pipefail
: "${LUMIERE_SUPABASE_SERVICE_ROLE_KEY:?Missing Codespaces Supabase secret}"
export LUMIERE_SUPABASE_URL="${LUMIERE_SUPABASE_URL:-https://sicszettmpnyniyhbhsl.supabase.co}"
export LUMIERE_SUPABASE_BUCKET=lumiere-private-photos
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH=backend python - <<'PY'
from services.supabase_photos import verify_private_bucket
if verify_private_bucket():
    print("PASS: intended customer bucket lumiere-private-photos is PRIVATE")
    print("No customer photos uploaded, downloaded or deleted.")
PY
