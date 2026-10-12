# Samsung Galaxy S22 Ultra — private Android API staging

Status: **prepared, not yet connected**. Expo Go navigation already passed through an
Expo Metro tunnel. Account login, private photo upload, colour analysis and Try-On
must wait until an authenticated private staging API is reachable from the phone.

## Recommended option: Tailscale Serve over a private tailnet

Tailscale supports GitHub Codespaces as a node and allows HTTPS reverse proxy to a
loopback-only API through **Serve**, restricted to members/devices authorized by the
tailnet policy. Do **not** use Tailscale Funnel (which opens a public endpoint).

Official setup:
- https://tailscale.com/docs/integrations/github/github-codespaces
- https://tailscale.com/docs/features/tailscale-serve
- https://tailscale.com/docs/how-to/set-up-https-certificates

1. Create/sign into a Tailscale account and install its Android app on the
   Samsung S22 Ultra, allowing its VPN connection. Keep devices restricted by
   tailnet access policy, preferably only your own approved account/device.
2. Add Tailscale's Codespaces devcontainer feature, **after** verifying that
   rebuilding the container will not destroy the existing MongoDB container or
   its persistent data. For this repository, prefer a new disposable staging
   Codespace rather than rebuilding the one with user accounts.
3. Join that staging Codespace to the same tailnet. Enable MagicDNS and HTTPS
   certificates per Tailscale's documented steps. Ensure machine-name privacy.
4. Run a disposable FastAPI staging service bound to `127.0.0.1` only,
   with a **separate** Mongo database and **separate private staging bucket**,
   and HTTPS recovery link specific to staging. Do not reuse the personal
   `lumiere-private-photos` bucket or existing user accounts for these tests.
5. On the Tailscale node, use `tailscale serve --bg 8015` (or equivalent
   for the selected staging port). Confirm status with `tailscale serve status`.
   **Never use `tailscale funnel`.** Turn Serve off when not testing.
6. Verify the resulting `https://<device>.<tailnet>.ts.net` URL is reachable
   from the Samsung while Tailscale is connected, but **not** from devices
   outside the tailnet. Confirm GET `/api/account/me` returns 401.
7. Restart Expo tunnel with a public (nonsecret) build-time origin only:
   ```bash
   cd frontend
   EXPO_PUBLIC_BACKEND_URL="https://YOUR-APPROVED-TAILNET-URL" npx expo start --tunnel --port 8082 --clear
   ```
   Restart the bundler rather than only reloading the QR code: Expo publicly
   embeds EXPO_PUBLIC_ variables into the app. Never put tokens, Resend keys,
   Supabase secret, auth headers or private identifiers in EXPO_PUBLIC_.
8. From Expo Go on Android, sign in to **disposable** staging accounts, upload
   synthetic/consented photos, verify ownership and deletion. App beta must
   still be promoted to a signed APK/internal build for device-specific tests.

## Current limitations
- A Metro tunnel is **not** an API tunnel. A private Codespaces HTTP port
  cannot be called by native Expo Go without a separate authenticated route.
- Expo Go may lack native libraries used by production builds.
- Native Android and iOS packages still use old StyleScan identifiers;
  plan an intentional package-name migration before distributing a real build.
- Use Android first; an actual iOS device signoff is a separate requirement.
- Tailnet access restriction **alone** does not replace FastAPI per-account
  authentication or production deployment security review.

## Safe initial check

From a terminal, run `command -v tailscale` to see if Tailscale is already
installed. Installing/connecting it requires account authorization. Do not
change devcontainer settings or launch a public tunnel until the existing data
and staging isolation plan have been confirmed.
