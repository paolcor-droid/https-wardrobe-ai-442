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
