# LUMIÈRE — reliable always-on hosting plan

Status: **planning only**. No production services, domain names, databases, photos or secrets have been changed.

## Why the Samsung preview stops
The Codespaces preview is hosted by Expo on port 8081 with a local FastAPI process (8000), Docker MongoDB (27018) and local photograph files. When the Codespace suspends, all of these stop. Process supervisors, keepalive pings or startup scripts cannot guarantee availability after Codespaces suspends and should not be used to defeat platform limits.

## Target architecture
- Deploy the Expo web build on a persistent HTTPS static web host; provide a fixed mobile-friendly app URL.
- Deploy FastAPI as an always-on service with health checks, automatic restarts, bounded resource usage and secure environment variables.
- Use a persistent managed database with network restrictions, encryption, backups and restoration tests.
- Use private object storage for uploaded and generated images; existing local photographs must be inventoried and migrated only with explicit approval. Never expose public buckets, service-role keys, or unauthenticated photograph URLs.
- Keep development Codespaces and production isolated, with distinct databases, buckets, secrets and domains.

## Before allowing customer traffic
1. Choose hosting vendor(s), billing account and location/data residency; collect user approval for paid services.
2. Inventory and back up existing MongoDB records and private local image files; verify restoration in a non-production environment.
3. Set up HTTPS domain and account/API routing, including web cookie same-origin/CSRF behavior and tight CORS allowlist.
4. Configure a persistent production database and private object bucket, then verify per-customer access and deletion with synthetic two-account tests.
5. Pass the photo deletion and backup-retention checks documented in PRE_LAUNCH_SECURITY_GATE.md and SUPABASE_PHOTO_STORAGE.md. Remote deletion from all backups cannot be assumed.
6. Set API keys only in server-side secret storage, configure cost limits, logging with no sensitive images or credentials, availability monitoring and alerts.
7. Test login, existing profiles, upload, preflight, Gemini Try-On, private image view/save, and account isolation on a Samsung using the fixed URL.
8. Perform a reversible staging rollout, approved data migration and cutover. Do not delete the Codespaces data or local files until the user explicitly approves and verifies successful migration.

## What cannot be fixed by dev-up.sh
An auto-restart inside a suspended Codespace will not start itself. Scheduled keepalive requests are not a reliable production hosting strategy.

## Immediate safe workaround
While using development preview, restart the existing Codespace and run `bash scripts/dev-up.sh` from Codespaces when available. This is not a permanent mobile availability solution.
