# LUMIÈRE beta release gates

This document is a release checklist, not a declaration that the app is safe to publish.

## Blocking: security and privacy
- [ ] Implement verified customer authentication (including session expiry and logout).
- [ ] Replace shared `default` profile with authenticated per-user database ownership.
- [ ] Enforce user ownership on every profile, feedback, wardrobe, photo, analysis, try-on, history and price-watch endpoint.
- [ ] Make media private by default; require authorization to access files.
- [ ] Implement irreversible deletion of owned source photos, generated try-ons and storage objects, with audit tests.
- [ ] Design and test a safe migration of legacy shared development data. Never assign shared records to a real customer automatically.
- [ ] Review CORS, API rate limiting, upload abuse, secrets and log redaction.
- [ ] Keep the public deployment fail-closed guard active until all checks above pass.

## Blocking: quality
- [ ] GitHub backend tests and frontend type checks pass on the exact release commit.
- [ ] Run end-to-end tests for onboarding, analysis, Discover, feedback, wardrobe, capsule planning and two-garment try-on.
- [ ] Validate skin analysis under varied lighting and skin tones; display uncertainty.
- [ ] Evaluate garment colour with manually labelled, clothing-only crops; do not claim background removal is clothing segmentation.
- [ ] Test image upload failure, storage outage, failed AI calls and recovery.

## Commercial launch
- [ ] Obtain retailer-feed permission and document source, refresh cadence and licensing.
- [ ] Test stale pricing and out-of-stock handling; do not promise live prices from catalogue snapshots.
- [ ] Connect a verified notification provider before enabling price alerts.
- [ ] Configure payments, validate signed webhooks and enforce subscription entitlements server-side.
- [ ] Publish accurate privacy terms, data retention rules, affiliate disclosures and beta limitations.
- [ ] Run a small opt-in beta with explicit feedback and crash monitoring.

## Current development claims
- Wardrobe and outfit planning use saved item labels, not verified garment pixels or live weather.
- Price snapshots can be compared offline; no live price feed or alerts are connected.
- Subscription billing is disabled.
- The production guard is a temporary fail-closed measure, not authentication.
- Do not remove the guard merely because CI passes.
