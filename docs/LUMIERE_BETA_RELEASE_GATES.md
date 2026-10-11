# LUMIÈRE — beta release gates

**Status: NOT CLEARED FOR PUBLIC LAUNCH.** This document tracks release blockers; a green unit-test check does not constitute a security or end-to-end sign-off.

## Required before any public access

- [ ] Account registration, sign-in, session expiry and password-reset flows implemented and tested.
- [ ] Every API route involving personal data requires authentication; no global/default shared profile.
- [ ] Wardrobe, preferences, colour analysis, conversations, feedback, uploads, try-ons, history and price targets scoped to authenticated owner in every read/write/delete operation.
- [ ] Private image storage with non-guessable, time-limited access or authenticated media proxy. Reject path traversal and cross-account file access.
- [ ] Permanent media erasure, including originals, generated derivatives, cached copies and backups according to documented retention windows; confirm actual storage deletion before claiming success.
- [ ] Data migration strategy for legacy shared/default records; do not silently assign legacy personal data to a new user.
- [ ] CSRF/session protections where relevant, restricted CORS, rate limits, safe upload limits and secret management.
- [ ] Production access gate remains enabled until independent security review and the above checks pass.

## Product reliability

- [ ] Backend and frontend CI green on development branch.
- [ ] Real-device signup, login, logout and session restoration.
- [ ] Two different face photos produce independently derived analyses; lighting and uncertainty surfaced.
- [ ] Preferences and avoided colours respected in Discover; no claims of image-verified garment colour when only supplier labels exist.
- [ ] Women's and men's product filters and out-of-stock exclusions verified with representative supplier snapshots.
- [ ] Wardrobe photo upload, list, two-item selection, try-on, capsule and deletion tested on Android and iOS.
- [ ] Failed photo uploads do not reuse previous images; invalid formats and oversized images rejected.
- [ ] Outfit planner uses user-selected climate only unless an actual weather provider is connected and permission is granted.
- [ ] Accessible error states, loading indicators, offline handling and small-screen layout tested.

## Commercial integrations

- [ ] Confirm supplier redistribution/image licences, stock synchronisation, delivery and returns policy.
- [ ] Price alerts require a permitted live retailer feed, change detection, opt-in notifications and opt-out controls. Offline snapshot comparisons are not live alerts.
- [ ] Subscriptions require payment provider account, verified server-side webhooks, receipt/entitlement checks, cancellations and refunds.
- [ ] Affiliate relationships and any ranking incentives disclosed.
- [ ] Legal review of privacy notice, terms, consumer claims, trademark and local consumer law.

## Quality metrics for a private beta

Track consented, privacy-minimised aggregate metrics: successful onboarding, analysis completion, recommendation saves/dislikes, wardrobe usage, try-on success/error rate and account/photo deletion success. Never commit photos, private supplier catalogues, payment secrets or personal analytics exports.

## CI interpretation

The development workflow compiles backend Python, runs focused unit tests and checks frontend TypeScript. It does **not** exercise MongoDB ownership, storage deletion, external AI/image models, supplier feeds, payments or real-device flows. These require separate integration tests and manual sign-off.
