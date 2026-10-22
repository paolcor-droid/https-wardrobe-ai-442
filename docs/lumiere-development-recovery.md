# LUMIÈRE development recovery (private)

The working MongoDB container is `lumiere-dev-mongo`. Never delete, rename or recreate it when startup reports an OCI runtime ID conflict. Stop/reopen the **existing** Codespace and rerun `bash scripts/start-lumiere-dev.sh`. Inspect with `bash scripts/diagnose-lumiere-docker.sh` before intervening in Docker.

## Backup and verification (Codespaces terminal)

1. With MongoDB running, use `bash scripts/backup-lumiere-dev.sh` to create a gzip-compressed archive and SHA-256 file under `.lumiere-backups/`. Keep the complete archive and matching `.sha256` file.
2. Run `bash scripts/verify-lumiere-backup.sh .lumiere-backups/<archive-name>.archive.gz`. This verifies the checksum, checks gzip integrity, restores into a **separate temporary database**, checks collection counts, then drops only that temporary database. It never restores onto the configured live database. If the test fails, review the output before treating the backup as recoverable. It does not audit application-level relationships.
3. Run `bash scripts/backup-lumiere-photos.sh` for **local** private photographs. If storage is S3 or Supabase, this script is **not** a backup of those providers; configure an appropriate independent private provider backup. Never put archives, credentials or sensitive filenames into GitHub.
4. Store **encrypted** copies of both database and photo archives outside the Codespace. The scripts do not upload them or set up a backup schedule, because offsite destination, retention and encryption credentials must be configured safely.
5. Record a copy of necessary deployment secrets separately in a secure secrets manager. The scripts deliberately do not include `.env` files.

## Recovery boundaries

Backups are sensitive personal information. Protect them with strong encryption and restricted access. Database backup and local private photos are separate assets; restoring only one may leave image references unresolved. The scripts do not back up S3, Supabase, Shopify, third-party accounts or provider history. A complete disaster recovery test should use an isolated environment and confirm account/photo references and deletion policies without exposing real customer data.

Existing backups created before checksum support may lack `.sha256` files; `verify-lumiere-backup.sh` safely refuses those, rather than claiming verification. Do not delete old archives simply because a newer file exists.

## After pulling changes

```bash
cd /workspaces/https-wardrobe-ai-442
git pull --ff-only origin lumiere-recommendations-v2
bash scripts/start-lumiere-dev.sh
bash scripts/backup-lumiere-dev.sh
bash scripts/backup-lumiere-photos.sh
ls .lumiere-backups/*.archive.gz
# Substitute one of the exact archive filenames from the listing:
bash scripts/verify-lumiere-backup.sh .lumiere-backups/<archive-name>.archive.gz
```

Treat commands with angle-bracket placeholders as examples, not literal executable commands. A restored backup may still be unusable if photo files and secrets are lost. Check local photo contents only in the private Codespace.
