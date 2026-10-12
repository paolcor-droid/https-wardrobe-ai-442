#!/usr/bin/env bash
# Safe, read-only staging preparation check. Does NOT install software, connect
# Tailscale, create containers, open ports, or touch original Codespace data.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ORIGINAL="potential-fortnight-97g7r4gj46x7h97jg"
echo "LUMIÈRE staging preflight"
if [[ "${CODESPACE_NAME:-}" == "$ORIGINAL" ]]; then
  echo "BLOCKED: original development Codespace detected; staging only." >&2
  exit 2
fi
if [[ -z "${CODESPACE_NAME:-}" ]]; then
  echo "BLOCKED: cannot confirm Codespace identity." >&2
  exit 2
fi
echo "PASS: separate Codespace detected (name withheld)"
branch="$(git branch --show-current)"
[[ "$branch" == "lumiere-recommendations-v2" ]] || { echo "BLOCKED: unexpected branch: $branch"; exit 2; }
echo "PASS: expected development branch"
command -v docker >/dev/null && echo "PASS: Docker CLI present" || echo "PENDING: Docker CLI missing"
command -v tailscale >/dev/null && echo "PASS: Tailscale CLI present" || echo "PENDING: Tailscale not installed"
if [[ -n "${LUMIERE_SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "INFO: Supabase secret present; never put in mobile bundle"
else
  echo "INFO: Supabase secret absent from staging (normal until explicitly scoped)"
fi
if [[ -n "${LUMIERE_RESEND_API_KEY:-}" ]]; then
  echo "INFO: Resend secret present; never put in mobile bundle"
else
  echo "INFO: Resend secret absent from staging (normal until explicitly scoped)"
fi
echo "PASS: read-only staging preflight finished; no infrastructure was changed"
