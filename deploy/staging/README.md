# LUMIÈRE private staging (deployment scaffold, not yet deployed)

This Docker Compose stack runs a production Expo Web export on Caddy and FastAPI behind an internal-only reverse proxy. `/api/*` remains same-origin for browser authentication and CSRF enforcement. **No MongoDB server is created here:** use a durable managed MongoDB instance. Private S3 or Supabase photo storage must be configured before API startup.

**Privacy default:** Caddy is bound to `127.0.0.1:8085` on the staging host. It is *not* a public website; use a trusted SSH tunnel for administrator inspection. Before allowing remote users or a mobile device, explicitly configure an external authenticated HTTPS gateway (e.g. managed identity access) and verify account authentication, CSRF, image deletion and mobile API routing. Do not open host port 8085 publicly.

Deployment preparation on an authorised Docker host:

1. Copy `.env.staging.example` to `.env.staging` and store real credentials only on that host (never in Git). Configure required private object-store credentials according to the backend's selected storage provider.
2. Run `python scripts/check-staging-config.py` with the intended staging environment loaded. The script checks only basic settings.
3. Run `docker compose -f deploy/staging/compose.yaml config` to inspect the configuration, then `docker compose -f deploy/staging/compose.yaml up --build -d` only after all safety/hosting requirements are approved.
4. On the host, `curl http://127.0.0.1:8085/health/ready` should return `{"status":"ready"}`. This is not a substitute for privacy and browser testing.
5. Implement external HTTPS identity gateway, certificate, backup/restore procedures and monitoring before distributing the staging URL.

**Important:** Expo native Android builds require an explicit `EXPO_PUBLIC_BACKEND_URL` HTTPS origin. Browser staging through this Caddy service uses same-origin API paths. The native app cannot use a loopback-only backend directly.

This is a deployment scaffold only. It has not been built, security-audited, run against real managed services, or released. Checkout and supplier ordering remain disabled in application logic.
