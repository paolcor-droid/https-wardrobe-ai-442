# LUMIÈRE pre-launch security and end-to-end gate

**Release state: BLOCKED.** Do not remove the backend public-access gate or deploy to public users on the basis of unit tests alone.

## Automated checks
- GitHub Actions: Python compile and backend account, isolation, photo privacy, storage-deletion helper, wardrobe, catalogue and service tests; Expo TypeScript build.
- Additional regression cases exercise two-customer private saved looks and product feedback, rejected cross-account reads/writes/deletes, and expired/revoked-session access.
- Tests use in-memory fake databases and storage callbacks. They are not real MongoDB, real storage, real AI or on-device end-to-end tests.

## Before production — mandatory live evidence
1. **Production authentication:** Validate full login/register, log out, expiration, throttling/brute-force protections, password-reset and recovery, secure token handling and supported web session design. Private Codespaces browser registration/login and HttpOnly cookie sessions have been exercised; production hosting, recovery and rate-limiting are not verified.
2. **Privacy and ownership:** Use two real test accounts in an isolated environment. Test account-switching and every Profile, Wardrobe, Discover, chat, photo, saved-look, price/feedback, and Try-On path. Verify bearer token never appears in logs and no customer identifier leaks via files, caches, CDN URLs, or legacy routes. Verify account deletion and retention/export policies.
3. **Photo deletion:** Verify the *live* provider's DELETE semantics and 404 read-back for the exact object key using an authorized dedicated test object. Confirm physical object and backup/CDN retention behavior, failure recovery and cascading references. Emergent deletion is unsupported. New uploads are configured for verified private Supabase Storage in development; keep the storage-retention gate.
4. **Mobile and web:** Test real iOS/Android builds, expiring sessions, interrupted network calls, image uploads and AI flows, user A vs B isolation, secure local persistence, deep links and navigation, crop/loading/error states.
5. **Deployment:** Review HTTPS, CORS and CSRF, server-side secrets, env configuration, logging/sensitive-data minimization, MongoDB unique indexes, backup/restore, vulnerability scan and an explicit go/no-go signoff.
6. **Editorial assets:** Confirm image source availability, copyright licence and any necessary model/commercial clearances.

## Known provisional limitations
- Web account cookie sessions work in the private Codespaces preview. Production public deployment remains closed; the legacy shared-data API remains protected.
- Private price alerts and caller-supplied recommendation preview are disabled on the client rather than risk legacy shared state.
- Legacy endpoints must remain blocked from all untrusted traffic until replaced or retired.
- Live Supabase API deletion and 404 read-back, two-account isolation, and manual UI deletion have passed in private Codespaces development. Provider backup/replica retention, real device and public deployment checks remain unverified.

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

## Storage deletion — Emergent built-in store cannot meet this requirement
Emergent's current glossary says its built-in Object Store does **not support
deletion** of uploaded assets. Source:
https://help.emergent.sh/glossary-of-emergent-terms

LUMIÈRE now refuses new customer photo uploads to the old Emergent object store.
Its existing customer-controlled **local** storage remains usable for development.
Existing Emergent photos are an unresolved retention issue requiring provider
support and/or policy review; do not claim those objects have been erased.

Private S3 storage is available behind `LUMIERE_PHOTO_STORAGE=s3` plus
`LUMIERE_S3_BUCKET` and host-provided AWS IAM credentials. The adapter uses
encryption, private application routes, deletion of object versions and markers,
then HEAD 404 verification. It refuses metadata deletion on a storage failure.
Configure bucket-level block-public-access, no public ACLs, no unreviewed Object
Lock/legal hold, and inspect versioning, lifecycle, replication, CDN and backup
policies. IAM requires S3 Put/Get/DeleteObject, ListBucketVersions and
DeleteObjectVersion. Do not commit AWS credentials to GitHub.

Run a real deletion check only in a dedicated disposable non-production bucket:
```bash
export LUMIERE_S3_BUCKET=your-lumiere-test-bucket
export LUMIERE_S3_TEST_BUCKET=your-lumiere-test-bucket
export LUMIERE_S3_TEST_ACK=delete-disposable-photo
python backend/scripts/verify_s3_photo_deletion.py
```
No S3 test bucket/IAM role was connected here; the live cloud deletion test is
**NOT executed**. A 404 after deletion does not prove purge from provider
backups, replicas, CDNs or legally retained copies. Verify contracts separately.

## Account recovery and security
- Login failure throttle: five failures per five minutes per IP+email; recovery
  throttle: three requests per hour. Both are **process-local development controls**,
  not a multi-worker distributed production rate limiter.
- One-time hashed password recovery token, 30-minute expiry, old-session
  revocation and recovery UI implemented and unit-tested.
- Recovery mail is **disabled without configured SMTP credentials**, a sender
  address, and HTTPS `LUMIERE_RECOVERY_BASE_URL`; it returns 503 instead of
  falsely claiming successful delivery.
- Session expiry and revocation have automated tests. Real timed expiry,
  multi-device refresh, shared-store throttle and account recovery mail
  delivery require staging verification.

## AI integration testing and provider choice
ChatGPT is the only customer-selectable text/analysis provider and the
Claude/ChatGPT selector and technical model label were removed. The backend
OpenAI chat model remains configurable via `LUMIERE_OPENAI_CHAT_MODEL`.
Gemini remains the image-rendering backend for virtual Try-On.

The repository includes `backend/scripts/live_ai_e2e.py` to validate real
ChatGPT styling, colour analysis, catalogue recommendations and Gemini Try-On.
It is opt-in because it incurs AI service charges and requires two consented
test photos, a local disposable backend, and configured API credentials. Do
not use personal photos until deletion is properly verified.

## Device validation
A real Android and iOS staging build is needed for each:
registration/login/logout, secure token storage, camera/photo selection,
upload errors and offline recovery, face analysis, wardrobe, Discover, Try-On,
account switching, logout privacy, session expiry, password reset link and
photo deletion. Never make the Codespaces backend publicly accessible to
test phones; use a separately secured staging backend.

## Release gates that remain
- Real iOS and Android device E2E on production-like builds, including
  session expiry, mobile photo picker, networking interruption and logout
- Live storage provider purge/retention verification, cascading deletion of
  photo references, account deletion/export and recovery procedures
- Distributed brute-force protection, configured SMTP account recovery/password reset, security review
- Production networking, secrets, monitoring, backup/restore and review
- Provider AI analyses and outfit/try-on integration with owner isolation
- Editorial photo licenses and any necessary releases

Do not claim production launch readiness until those checks have evidence.

## Verified Supabase private-development rollout — 12 October 2026
- Dedicated `lumiere-private-test` bucket was verified private. Real synthetic upload, authenticated read, delete and read-back absence passed.
- Two-account synthetic live FastAPI integration against real Supabase Storage passed owner-only view/delete, logout/revocation and cross-user isolation on an isolated MongoDB.
- Intended `lumiere-private-photos` customer bucket was confirmed private using the admin bucket endpoint.
- User reported existing saved colour analysis/photo still displayed after switch, new photo saved to the customer bucket, new colour analysis displayed, and deletion via You removed the object from the bucket.
- Local image read/delete is retained with `LUMIERE_LOCAL_IMAGE_STORAGE=1`; this is *not* a media migration or backup guarantee.
- Public release remains BLOCKED. Provider backup/replica retention response, production SMTP email delivery, distributed throttling, signed real iOS and Android tests, deployment-security review and production data lifecycle policies remain outstanding.

## Read-only go/no-go preflight
`PYTHONPATH=backend python backend/scripts/release_preflight.py` gives a non-secret configuration checklist and returns nonzero on blocked items. Environment flags are operator attestations **not technical proof**; attach vendor documentation and actual signed test records before a release decision. Never set these flags merely to make the checker green.

## 12 October 2026 browser confirmations and automated regression
- User confirmed that Resend testing-sender recovery email arrived at an authorized test inbox. **Full reset-token, prior-session revocation and expiry remain unverified in live SMTP flow.** Mocked backend test verifies single-use token and revocation, and new unit tests verify SMTP STARTTLS, message address and encoded HTTPS link.
- User confirmed post-login redirect to You and access to Discover, Stylist, Wardrobe and Try-On after the navigation fix. This is a development browser check, not a device signoff.
- No production secrets, real passwords or private customer photographs were used in the mocked recovery SMTP tests.

## Direct Gemini Try-On (development integration)
- Server-side `GEMINI_API_KEY` switches private Try-On directly to Google's
  `gemini-3.1-flash-image` generateContent API, bypassing Emergent. Never use
  the browser or Expo environment to hold the API key.
- Add `GEMINI_API_KEY` as a repository-scoped GitHub Codespaces secret (or
  provision as a backend-only deployment secret). Restart the Codespace and
  FastAPI to load it. Confirm presence without printing its value:
  `python -c 'import os; print(bool(os.getenv("GEMINI_API_KEY")))'`.
- `LUMIERE_GEMINI_IMAGE_MODEL` allows only the supported, allowlisted
  `gemini-3.1-flash-image` or `gemini-2.5-flash-image` IDs.
- If no Gemini key is provided, the existing Emergent provider is used.
  A failed direct request is *not* silently retried through Emergent.
  Provider body, key and photographs must never be included in logs.
- This is implemented and unit tested, **not verified with a real Gemini key**.
  Check billing, provider data processing terms, response validity and
  account-specific photo retention before production use. Keep public launch
  blocked until a real end-to-end Try-On succeeds.
