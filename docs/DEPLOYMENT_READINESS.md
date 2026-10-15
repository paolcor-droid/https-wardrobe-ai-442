# LUMIÈRE deployment plan (private development → persistent hosting)

## Private Codespaces preview (currently supported)

From the repository root, after the branch is pulled:

```bash
bash scripts/start-lumiere-dev.sh
```

The script starts the EXISTING `lumiere-dev-mongo` container, waits for MongoDB, and starts FastAPI (8000) and Expo Web (8081). It neither creates nor deletes a database and refuses to replace already running API or frontend processes. Check `.lumiere-dev-logs/` for startup errors. Keep this terminal open and use the forwarded **8081** URL. Do not forward port 8000 or 27017 publicly.

Readiness endpoints for a future reverse proxy/load balancer: `GET /health/live` checks the process; `GET /health/ready` also checks MongoDB and returns HTTP 503 when the database is unavailable. Keep these behind appropriate edge controls in staging or production; neither exposes account data. The development launcher now waits for `/health/ready`, not merely an open TCP port. These new changes require running verification tests in Codespaces before use.

**This is not persistent hosting.** GitHub Codespaces can suspend; neither a startup script nor an autostart setting can keep the application online when Codespaces is suspended. The desktop/mobile browser preview depends on Metro and a same-origin proxy, so it is not a production deployment.

## Before public hosting

1. **Persistent database**: move to a managed private MongoDB service with TLS, backups and database migration/recovery testing. Do not copy private customer records to a test instance without explicit authorization.
2. **Private object storage**: current local image storage is only appropriate for Codespaces. Configure authenticated durable storage; verify photos cannot be retrieved across accounts and that deletion removes generated images.
3. **Backend security**: HTTPS domain and strict CORS/CSRF origin validation, secure cookie configuration, durable distributed rate limiting, secure environment secrets, structured redacted errors, database indexes, logging/monitoring, and readiness checks.
4. **Frontend deployment**: build a static production Expo Web bundle; serve it from a persistent HTTPS host. Route `/api/*` through that host's reverse proxy to the private FastAPI service (maintains same-origin cookie/CSRF protection). Do not publish Metro, development QR codes, or the Codespaces port as a storefront.
5. **AI credentials**: inject direct OpenAI/Gemini credentials only server-side; configure spending limits and verify model access. Never add API keys to Git or browser bundles.
6. **Commercial readiness**: all catalogue prices/stock are presently unverified snapshots. Checkout and order placement must stay disabled until supplier contracts, stock checks, shipping, consumer terms, taxes and payment processing are verified.
7. **Deployment gate**: `cd frontend && npx tsc --noEmit`; `cd backend && python -m pytest -q tests/test_account_routes.py tests/test_discover_search.py tests/test_supplier_catalogue_store.py tests/test_shopify_test_adapter.py`; then conduct browser/mobile smoke tests with disposable accounts and verify photo deletion.

**No production hosting provider, domain, database or storage account has been selected or provisioned by this change.** Do not claim LUMIÈRE remains available after Codespaces suspension until a persistent deployment has actually been configured and smoke-tested.

## Repeatable predeployment checks

Run `bash scripts/verify-lumiere.sh` from the repository root. This performs backend syntax checks, the existing targeted Python regression suites, frontend TypeScript validation, and a check for accidentally tracked development secrets. It is read-only and neither starts services nor accesses customer accounts. It is a development verification gate, **not** a production security audit or a deployment. CI and real staging browser tests are still needed before launch.

## Staging environment preflight

Run `python scripts/check-staging-config.py` **only after supplying a staging environment**. It checks for an external MongoDB URL (and TLS when using `mongodb://`), explicit HTTPS CORS origins, disabled local photo storage, selected durable photo backend, database name and presence of a server-side OpenAI key. It prints no secrets, makes no network calls and does not deploy anything. Passing this preflight does **not** prove a bucket is private, authenticate a real account, verify a live database or validate payments. The GitHub Actions workflow runs with read-only repository permissions and bounded job runtimes.

## Container staging scaffold (not yet online)

See `deploy/staging/README.md` for two Docker images and a Compose manifest serving Expo Web via Caddy and the private FastAPI service. Ports bind **only to 127.0.0.1** until an authenticated TLS access gateway is configured. A root `.dockerignore` excludes local secrets, image storage, customer catalogue snapshots and development logs from build context. The scaffold still needs a managed MongoDB, private object store, build/runtime validation and approval for a chosen host. It must not be described as a persistent deployment yet.
