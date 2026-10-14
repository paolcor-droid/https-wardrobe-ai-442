# LUMIÈRE — public release readiness plan (14 October 2026)

**Decision: NOT PUBLIC-READY.** This document tracks release gates, not a deployment authorization. Keep `main` and public-access restrictions unchanged. Development continues on `lumiere-recommendations-v2`.

## Current working baseline
- Samsung Chrome private Codespaces preview works when services are running; development Codespace can suspend.
- Owner-specific login, catalogue browsing, product feedback, private photo upload/view/delete and Try-On history have been exercised in development.
- Direct Gemini produced at least one successful real image; other photo/garment combinations were filtered. Treat one successful run as smoke evidence, not a reliability benchmark.
- Local no-cost Try-On preflight screens for brightness, size, framing, contrast and image detail. It is **not** a validated pose or garment fit detector; deliberately warns and lets customer opt in.
- Colour/profile recommendation scoring and catalogue feedback are implemented; trial snapshot **does not represent real-time inventory**.
- Supabase private photo test bucket and customer bucket development checks are described in PRE_LAUNCH_SECURITY_GATE.md; backup retention and production end-to-end evidence remain open.

## Priority 0 — mandatory before public exposure

| Gate | Required proof | Status |
| --- | --- | --- |
| Stable hosting | Production frontend, always-on API and persistent DB independent of Codespaces; health/uptime alert and recovery procedure | BLOCKED: user elected to retain private Codespaces for development |
| Private photo storage and deletion | Written storage retention/backup policy; live synthetic delete/readback and cross-account tests in final hosting environment; cascading deletion and account deletion/export | PARTIAL: private development checks passed; production lifecycle open |
| Security | Independent review of all legacy routes, CSRF/CORS, permissions, rate limits, password reset, sessions, secrets, dependencies, abuse limits | OPEN |
| Auth and recovery | Production email delivery, password reset, revoked/expired session, recovery failover and multi-device testing | PARTIAL: development email received; full production scenario open |
| Data protection | Privacy policy, terms, consent for AI photo processing, GDPR/Australian Privacy Principles assessment as applicable, provider processing and retention terms | OPEN |
| Real-device E2E | Android and iOS tested against staging using at least two synthetic accounts, ownership separation, offline/network errors, upload, Gemini, deletion, zoom and save | PARTIAL: Samsung browser smoke only |
| Data durability | Database backup + verified restore, private image backup strategy, migration rollback, no accidental destruction of local Codespaces photos | OPEN |
| Real Gemini reliability and budget | Consented repeatable sample set, filtered/error/success outcome counts, cost-per-try-on, timeouts and rate-limit handling; no implicit paid retries | PARTIAL |
| Supplier/customer rights | Legal right to display imported photos/catalogue/prices; actual stock, taxes, shipping, returns, supplier sync or clear referral-only mode | OPEN |
| Release decision | Named owner signs off all gates with evidence and rollback plan | BLOCKED |

## Priority 1 — product readiness (before wider beta)
1. **Try-On**: no-cost preflight can only quantify basic image characteristics. Add consented pose/body-framing detection with measured precision/false warning rates; interpret selected garment type without needing user-entered description; explain refusals without implying that rejection proves an image is inappropriate. Test with multiple lighting conditions, poses, skin tones and garments. Never silently resend images to another vendor.
2. **Recommendations**: validate profile, climate, colour, avoided colours, department and budget constraints. Test the existing liked/saved/purchased boost and avoid overfitting to one purchase. Display relevant `recommendation_reasons`; don't claim image-derived garment colour verification when only supplier labels are checked.
3. **Catalogue quality**: make product image availability and size selection clear; no fabricated stock/retailer links. Integrate verified stock feeds before transactional checkout.
4. **UX/accessibility**: loading, cancellation, text size, tap targets, TalkBack, empty states, save to Android Downloads/Gallery distinction, photo deletion and understandable network/retry messages.
5. **Account lifecycle**: full delete/export flow including analyses and saved looks, retention and recovery wording; age/consent handling if required.
6. **Observability**: anonymous request ID and provider error category/counts, success/latency metrics and budget alerts without recording photographs, API keys or personal message content.

## Priority 2 — after controlled beta
- Visual body pose suitability validation using an on-device or backend model with privacy review.
- Reliable multi-retailer inventory/price integration, brand coverage and merchant terms.
- Wardrobe learning from explicit feedback and purchases with explainability and user correction controls.
- Production PWA installation/offline shell and push notifications only after controls and permissions review.

## Test and rollout sequence
1. Preserve private Codespaces as working development baseline. Make small changes on `lumiere-recommendations-v2` and require CI.
2. Build a **disposable** staging environment with synthetic accounts/photos, production-equivalent authentication, storage and network settings. Never expose current local Codespaces API publicly.
3. Run an automated synthetic matrix: bright/dark, clear/blurred, wide/portrait, upper/full-body images; tops/trousers/dresses, one/two garments; provider success/filtered/429/timeout; user A/B access denial; deletion and backup restore.
4. Conduct supervised manual Samsung and iOS testing, capture pass/fail results and cost estimates. Use personal photos only after explicit consent and validated deletion pathway.
5. Complete legal/editorial/business documents and independently review security.
6. Sign off gated limited-access beta. Review metrics and support needs before public release.

## Explicitly not done
- No 24/7 hosting or production migration chosen.
- No verified high-accuracy pose/garment-fit model.
- No audited end-to-end release test across real users.
- No public deployment, database deletion or implicit photo migration.

References within repository: `docs/PRE_LAUNCH_SECURITY_GATE.md`, `docs/SUPABASE_PHOTO_STORAGE.md`, `docs/ALWAYS_ON_HOSTING_PLAN.md`.

## 15 October 2026 incremental security and privacy implementation
- Optional local MediaPipe Pose landmarks were wired into the no-cost photo preflight; `backend/requirements-pose.txt` is not installed by the standard development environment. The endpoint responds `pose_detection: unavailable` if the local model is absent. No photos go to a third-party pose service. Do not claim body pose has been validated on Samsung or in CI without a real landmark model installed and live validation.
- Private `GET /api/account/account/export` now offers a bounded JSON **metadata** export. It excludes raw photographs, password hashes, session records and storage paths. This is not yet a complete GDPR-style portable data export with photo binaries.
- Account deletion preview and password-confirmed deletion remain **disabled for real deletion by default** (`LUMIERE_ENABLE_ACCOUNT_DELETION` unset). Never enable on existing customer accounts before external storage retention, interrupted-deletion recovery, audit and data-backup obligations are reviewed.
- Added in-memory disposable account tests for cross-account export isolation and deletion disabled-by-default. Production hosting, full reset-mail E2E, backup retention and independent security review remain blocked.


## 15 October 2026 targeted security review: findings (NOT independent audit)
- **Critical release blocker**: Codespaces is not always-on hosting. No production cutover.
- **High**: Account deletion currently deletes individual photo objects before database cleanup. A provider failure part-way through leaves a recoverable but partially missing photo set. Do not enable the deletion feature until there is a resumable deletion ledger, a reversible plan, idempotent provider operations and fully tested backup/retention semantics.
- **High**: Exported ZIP photographs constitute sensitive personal data even though the route is authenticated, no-store, owner-scoped and size-bounded. Verify browser download history, CSRF/session expiry, cache-control, no CDN caching and support for large exports in staging. ZIP export is a separate route from JSON metadata export.
- **High**: Recovery email delivery and reset+session-revocation have not been verified together on a production-like email provider. Unit test success is not evidence of actual inbox delivery.
- **Medium**: Pose model is optional and not installed in the normal runtime. Its landmark test uses synthetic fake model output, not an empirical test for human pose detection; false-negative and false-positive rates remain unmeasured.
- **High**: Independent external penetration/security assessment and privacy/legal review have **not** been commissioned or performed. An assistant-authored code review is not independent evidence.

### Live verification protocol (requires user-controlled credentials and disposable accounts)
1. On a separate staging backend, install optional `backend/requirements-pose.txt` after checking Python/runtime support, run `PYTHONPATH=backend pytest -q backend/tests/test_tryon_preflight.py`, then use a consented synthetic/stock photograph to check the actual `pose_detection` field. Never upload real customer photos to external test services.
2. In the isolated disposable environment, create two synthetic accounts and verify export ZIP contains only the owner's synthetic photos. Run export over HTTPS and check session/logout failure paths.
3. For password recovery, use an authorized disposable inbox with configured sender. Request reset; actually receive email, consume the link, verify old sessions fail, verify the link cannot be replayed, and verify other reset links for the account are revoked. Never post reset tokens to chat or logs.
4. Use a dedicated **disposable private storage bucket** and separate test database only. Test account-delete success, provider failure at first/middle/last photo, retry and restored state. Do not enable `LUMIERE_ENABLE_ACCOUNT_DELETION` on a backend holding real customer accounts.
5. Commission an independent penetration/security assessment and a qualified privacy/data-processing legal review before any public release.

