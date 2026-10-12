# LUMIÈRE pre-launch security and end-to-end gate

**Release state: BLOCKED.** Do not remove the backend public-access gate or deploy to public users on the basis of unit tests alone.

## Automated checks
- GitHub Actions: Python compile and backend account, isolation, photo privacy, storage-deletion helper, wardrobe, catalogue and service tests; Expo TypeScript build.
- Additional regression cases exercise two-customer private saved looks and product feedback, rejected cross-account reads/writes/deletes, and expired/revoked-session access.
- Tests use in-memory fake databases and storage callbacks. They are not real MongoDB, real storage, real AI or on-device end-to-end tests.

## Before production — mandatory live evidence
1. **Production authentication:** Validate full login/register, log out, expiration, throttling/brute-force protections, password-reset and recovery, secure token handling and supported web session design. Private Codespaces browser registration/login and HttpOnly cookie sessions have been exercised; production hosting, recovery and rate-limiting are not verified.
2. **Privacy and ownership:** Use two real test accounts in an isolated environment. Test account-switching and every Profile, Wardrobe, Discover, chat, photo, saved-look, price/feedback, and Try-On path. Verify bearer token never appears in logs and no customer identifier leaks via files, caches, CDN URLs, or legacy routes. Verify account deletion and retention/export policies.
3. **Photo deletion:** Verify the *live* provider's DELETE semantics and 404 read-back for the exact object key using an authorized dedicated test object. Confirm physical object and backup/CDN retention behavior, failure recovery and cascading references. Keep `LUMIERE_REMOTE_DELETE_ENABLED` disabled until validated.
4. **Mobile and web:** Test real iOS/Android builds, expiring sessions, interrupted network calls, image uploads and AI flows, user A vs B isolation, secure local persistence, deep links and navigation, crop/loading/error states.
5. **Deployment:** Review HTTPS, CORS and CSRF, server-side secrets, env configuration, logging/sensitive-data minimization, MongoDB unique indexes, backup/restore, vulnerability scan and an explicit go/no-go signoff.
6. **Editorial assets:** Confirm image source availability, copyright licence and any necessary model/commercial clearances.

## Known provisional limitations
- Web account cookie sessions work in the private Codespaces preview. Production public deployment remains closed; the legacy shared-data API remains protected.
- Private price alerts and caller-supplied recommendation preview are disabled on the client rather than risk legacy shared state.
- Legacy endpoints must remain blocked from all untrusted traffic until replaced or retired.
- Live object-store deletion is not yet verified and cannot be claimed complete based solely on mocked tests.

## Codespaces development start (private only)
Run `bash scripts/dev-up.sh` from the repository root. The script starts **only the
existing** `lumiere-test-mongo-2` Docker container, waits for its ping, starts
FastAPI bound to 127.0.0.1:8000 and Expo web on 8081 as needed, and reports
health. It does not alter port visibility or automatically replace/delete the
database. Logs live under `.lumiere-dev/` (keep private). The Docker OCI
"container with given ID already exists" problem may require stopping and
restarting the Codespace; this script cannot repair the host's runtime.
No services survive a stopped Codespace.

## Extended live integration tests (opt-in)
From a running isolated disposable database:
```bash
LUMIERE_LIVE_TEST_ACK=disposable-database \
LUMIERE_LIVE_API_URL=http://127.0.0.1:8000 \
python backend/scripts/live_account_smoke.py
```
Includes two-account authentication, profile separation, an in-memory generated
(non-personal) image upload, cross-owner read/delete denial, owner deletion and
404 readback, logout and token revocation. Run this on an isolated disposable
development database **only**: it creates records.

## Remote provider deletion: verification still BLOCKED
The test script `backend/scripts/verify_remote_photo_deletion.py` is gated by
`LUMIERE_DELETION_TEST_ACK=delete-disposable-object`,
`LUMIERE_STORAGE_TEST_ISOLATED=yes`, `LUMIERE_STORAGE_TEST_URL`,
`LUMIERE_STORAGE_TEST_KEY`, and `LUMIERE_DELETION_TEST_OBJECT`.
It reads a dedicated disposable object first (must return 200), requests deletion,
then requires 404 read-back. **This is a destructive operation**; do not run
against production objects, customer images, or a production bucket.
Credentials must be supplied through secret environment variables, never
committed. Because no configured isolated provider test object/credentials are
available here, the live remote-provider test has **not been executed**.
Even a successful 404 does not establish backend purge, backups, CDN or
retention periods; confirm these separately with the storage provider before
enabling `LUMIERE_REMOTE_DELETE_ENABLED=1`.

## Release gates that remain
- Real iOS and Android device E2E on production-like builds, including
  session expiry, mobile photo picker, networking interruption and logout
- Live storage provider purge/retention verification, cascading deletion of
  photo references, account deletion/export and recovery procedures
- Brute-force protection, account recovery/password reset, security review
- Production networking, secrets, monitoring, backup/restore and review
- Provider AI analyses and outfit/try-on integration with owner isolation
- Editorial photo licenses and any necessary releases

Do not claim production launch readiness until those checks have evidence.
