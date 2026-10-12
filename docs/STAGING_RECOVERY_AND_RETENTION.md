# LUMIÈRE — staging recovery and provider retention approval

**Current gate:** private Codespaces browser Supabase photo deletion is verified; public release remains blocked.

## SMTP setup and real-delivery acceptance

The current account recovery service needs these **server-only** environment settings:
`LUMIERE_SMTP_HOST`, `LUMIERE_SMTP_PORT` (default 587),
`LUMIERE_SMTP_USER`, `LUMIERE_SMTP_PASSWORD`,
`LUMIERE_RECOVERY_FROM`, and `LUMIERE_RECOVERY_BASE_URL`
(an actual HTTPS staging origin serving `/account`).

Use an authenticated TLS SMTP provider and verify sender/domain authentication
(SPF, DKIM, DMARC). Store the password in staging secret management, not
GitHub source, app bundle, terminal history, tickets, screenshots or chat.
Do not configure the password in Expo. Current code uses STARTTLS, so an
SMTP provider requiring implicit TLS/port 465 needs a deliberate adapter.

Use two **disposable staging accounts** and an address you control:
1. Request recovery for account A and check receipt and subject, sender and
   HTTPS reset URL (never log or share the token).
2. Confirm one-use token validity and 30-minute expiry; use it once to
   change A's password.
3. Confirm the old A password and all pre-reset A sessions fail; new A
   credentials work; B stays unaffected.
4. Confirm repeated token use fails and a nonexistent address is not exposed.
5. Test mail outage returns a safe error and expired-token UI recovery.
6. Test staged request throttling across multiple workers/replicas, not
   only the current process-local throttle.

No live SMTP delivery has been performed by ChatGPT. Do not mark complete
until recorded with a staging mail provider.

## Supabase Storage support query — ready to submit

Subject: Private Storage object deletion — replica, backup and CDN retention

We are assessing Supabase Storage for a consumer styling application where
users can upload identifiable photographs and delete them through the app.
We have verified private-bucket upload, authenticated retrieval, DELETE
acknowledgment, and 404/read-back absence on a Sydney-region project.

Could you please confirm in writing:
- After Storage API DELETE, maximum retention of actual image bytes in
  replicas, provider-managed backups, deleted-object recovery systems,
  logs and caches; and any exceptions.
- Whether Storage backups include image bytes or only metadata, and whether
  deleted image bytes can be restored by Supabase support.
- Whether private authenticated object URLs are cached at the CDN or edge
  and the maximum invalidation/expiry time after deletion, including Free plan.
- Available data-processing agreement (DPA), subprocessors, storage
  residency/replication, account-erasure procedures and incident support.
- Whether additional bucket/project settings are required for deletion
  expectations under Australian Privacy Principles and GDPR where applicable.

Please distinguish normal active-bucket unavailability from guaranteed
physical purge across backups/replicas. We will not claim such a guarantee
without a documented basis.

## Release sign-off fields

| Check | Owner/evidence | State |
|---|---|---|
| Supabase active-object deletion and owner-isolation | Codespaces synthetic and manual UI tests 2026-10-12 | Pass, private development |
| Supabase replica/backup retention | Vendor written response required | BLOCKED |
| Real SMTP recovery email and expiry/revocation | Staging delivery report required | BLOCKED |
| Shared multi-instance rate limiting | Implementation and load/abuse tests required | BLOCKED |
| Signed Android & iOS M01–M18 | Separate device reports required | BLOCKED |
| Production HTTPS/CORS/CSRF/security/privacy review | Owner-approved report required | BLOCKED |
