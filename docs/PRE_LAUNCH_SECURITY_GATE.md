# LUMIÈRE pre-launch security and end-to-end gate

**Release state: BLOCKED.** Do not remove the backend public-access gate or deploy to public users on the basis of unit tests alone.

## Automated checks
- GitHub Actions: Python compile and backend account, isolation, photo privacy, storage-deletion helper, wardrobe, catalogue and service tests; Expo TypeScript build.
- Additional regression cases exercise two-customer private saved looks and product feedback, rejected cross-account reads/writes/deletes, and expired/revoked-session access.
- Tests use in-memory fake databases and storage callbacks. They are not real MongoDB, real storage, real AI or on-device end-to-end tests.

## Before production — mandatory live evidence
1. **Production authentication:** Validate full login/register, log out, expiration, throttling/brute-force protections, password-reset and recovery, secure token handling and supported web session design. Web sessions intentionally fail closed; do not represent web login as complete.
2. **Privacy and ownership:** Use two real test accounts in an isolated environment. Test account-switching and every Profile, Wardrobe, Discover, chat, photo, saved-look, price/feedback, and Try-On path. Verify bearer token never appears in logs and no customer identifier leaks via files, caches, CDN URLs, or legacy routes. Verify account deletion and retention/export policies.
3. **Photo deletion:** Verify the *live* provider's DELETE semantics and 404 read-back for the exact object key using an authorized dedicated test object. Confirm physical object and backup/CDN retention behavior, failure recovery and cascading references. Keep `LUMIERE_REMOTE_DELETE_ENABLED` disabled until validated.
4. **Mobile and web:** Test real iOS/Android builds, expiring sessions, interrupted network calls, image uploads and AI flows, user A vs B isolation, secure local persistence, deep links and navigation, crop/loading/error states.
5. **Deployment:** Review HTTPS, CORS and CSRF, server-side secrets, env configuration, logging/sensitive-data minimization, MongoDB unique indexes, backup/restore, vulnerability scan and an explicit go/no-go signoff.
6. **Editorial assets:** Confirm image source availability, copyright licence and any necessary model/commercial clearances.

## Known provisional limitations
- Web account sessions are intentionally not enabled and public route gate remains closed.
- Private price alerts and caller-supplied recommendation preview are disabled on the client rather than risk legacy shared state.
- Legacy endpoints must remain blocked from all untrusted traffic until replaced or retired.
- Live object-store deletion is not yet verified and cannot be claimed complete based solely on mocked tests.
