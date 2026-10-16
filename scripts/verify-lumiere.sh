#!/usr/bin/env bash
# Read-only verification for LUMIÈRE before deployment.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "[1/4] Python syntax verification"
python -m py_compile backend/server.py backend/services/account_routes.py
echo "[2/4] Backend regression tests"
(cd backend && python -m pytest -q tests/test_demo_catalogue.py tests/test_demo_outfit_quality.py tests/test_staging_preflight.py tests/test_account_routes.py tests/test_discover_search.py tests/test_supplier_catalogue_store.py tests/test_shopify_test_adapter.py)
echo "[3/4] Frontend TypeScript validation"
(cd frontend && npx tsc --noEmit)
echo "[4/4] Verify no development secrets tracked by Git"
if git ls-files | grep -E '(^|/)(\.env|\.env\.local|\.lumiere-dev-logs)(/|$)' | grep -v -E '\.env\.example$'; then
  echo "Potentially sensitive development file is tracked; inspect before deployment." >&2
  exit 1
fi
echo "Local validation passed. Production security, browser, storage and supplier checks are still required."
