# Private Android staging implementation checklist

**Codespace identified for staging:** `solid-space-waffle-g4v4jwv7wr7gh9r7v`.
**Original, protected development Codespace:** `potential-fortnight-97g7r4gj46x7h97jg`.

No staging infrastructure is installed, deployed, authenticated, or exposed by these notes.

## Completed without user involvement
- The separate Codespace and `lumiere-recommendations-v2` branch were confirmed by terminal output.
- Android S22 Ultra Expo Go successfully opened Stylist, Discover, Wardrobe,
  Try-On and You over the Expo tunnel (UI navigation only; private API untested).
- `scripts/staging-preflight.sh` provides a read-only guard that refuses
  to proceed from the original Codespace.
- Expo's `frontend/src/backend-origin.ts` already refuses missing or
  non-HTTPS native account API origins.

## Pending explicit account/device steps
- Connect staging Codespace to the owner's Tailscale tailnet. Requires account
  authorization. **Tailscale Serve, never Funnel**; do not open 8000 or MongoDB.
- Provision a **dedicated disposable staging** MongoDB volume/service and
  test-only Supabase private bucket, independent of existing personal accounts.
- Review TLS, endpoint access policy and API-owned route checks before exposing
  a staging API through the private tailnet.
- Configure native Expo `EXPO_PUBLIC_BACKEND_URL` with the approved tailnet
  HTTPS origin; a Metro tunnel alone only delivers application JS.
- Perform physical Samsung API/login/photo tests with synthetic fixtures.
- Produce Android installation build and verify real native-device behavior.

## Operator preflight when available
```bash
cd /workspaces/https-wardrobe-ai-442
git pull --ff-only origin lumiere-recommendations-v2
bash scripts/staging-preflight.sh
```
This does not change the original environment or expose any service.

Do not paste secrets or recovery links into chat or commit them to source.
Do not run `docker system prune`, recreate/remove the old MongoDB container,
or change the original Codespace port access.
