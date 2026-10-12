# LUMIÈRE — private Supabase photo storage

## What stays the same
FastAPI authenticates users and checks MongoDB photo ownership. Expo clients
only access `/api/account/photos` through FastAPI; they never receive a
Supabase service-role key or a public photo URL. MongoDB is unchanged.

## Setup (user action — do NOT send keys via chat)
1. Create a Supabase project at https://supabase.com/dashboard.
2. In Storage, create a bucket named `lumiere-private-photos`.
   **Keep it PRIVATE**, not public. Set image MIME restrictions and an 8 MB
   upload limit if available. Do not add publicly permissive SELECT policies.
3. Obtain your project URL and server-side secret/service-role key from
   Supabase settings. Configure them **only in secure backend environment
   variables**, never in `EXPO_PUBLIC_*` or Git. Supabase service-role keys
   bypass RLS and must not be sent to web/mobile clients.
4. Set in the **staging backend only**:
   `LUMIERE_PHOTO_STORAGE=supabase`
   `LUMIERE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
   `LUMIERE_SUPABASE_BUCKET=lumiere-private-photos`
   `LUMIERE_SUPABASE_SERVICE_ROLE_KEY=(secret configured securely)`
5. Restart staging FastAPI, and verify photos upload, are owner-only, and
   can be deleted. **Do not flip Codespaces development to Supabase yet.**
   The existing `bash scripts/dev-up.sh` uses private local files.

## Deletion smoke on a disposable *separate* Supabase test project
Create a separate PRIVATE bucket `lumiere-private-test`. Configure
the same server-side environment variables but point to the test project
and bucket. Then run:
```bash
LUMIERE_SUPABASE_TEST_ACK=delete-synthetic-test-image \
LUMIERE_SUPABASE_TEST_BUCKET=lumiere-private-test \
python backend/scripts/verify_supabase_photo_deletion.py
```
This generates a harmless synthetic image, uploads it, reads it through
authenticated Storage, deletes it, and requires an unsuccessful read-back.
This **has not run yet** because no Supabase project credentials exist.

## Key privacy limits
- REST deletion and a missing object read-back are NOT evidence that
  backups, replicas, caches or historical copies have been physically erased.
  Review Supabase's retention, backup and data-processing terms separately.
- The current server checks photo ownership, and only the server uses a
  highly privileged storage key. Project configuration must protect it.
- There is no automatic migration of older local or Emergent images.
  Existing photos remain where they were until a separately reviewed migration.
- Until Supabase is configured and deletion tested, public launch stays blocked.
- Keep bucket private; never use public Storage URLs or persistent signed URLs
  for sensitive face photographs.

## Live two-account Supabase storage and API isolation test
After the synthetic test-bucket deletion check has passed, run the new
isolated integration test against the **same PRIVATE TEST bucket only**:
```bash
cd /workspaces/https-wardrobe-ai-442
LUMIERE_SUPABASE_URL=https://sicszettmpnyniyhbhsl.supabase.co \
LUMIERE_SUPABASE_BUCKET=lumiere-private-test \
LUMIERE_SUPABASE_TEST_BUCKET=lumiere-private-test \
LUMIERE_SUPABASE_ACCOUNT_E2E_ACK=test-bucket-disposable-database \
python backend/scripts/verify_supabase_account_isolation.py
```
The script checks Supabase bucket `public=false`, starts **a separate
FastAPI process on 127.0.0.1:8012** with a disposable MongoDB database,
creates two artificial accounts, uploads an in-memory synthetic image,
verifies owner-only access and rejection of other-account reads/deletes,
deletes the photo and checks 404, then stops the isolated test backend.

Never make port 8012 public. This command does not switch the normal
LUMIÈRE app on 8000/8081, edit real profiles, or migrate files. It
requires a running local MongoDB container and the existing Codespaces
Supabase service-role secret. Test credentials are not echoed.

## Production-bucket rollout gate
After the test passes:
1. Verify `lumiere-private-photos` bucket is **private** in the dashboard.
2. Configure `LUMIERE_PHOTO_STORAGE=supabase`,
   `LUMIERE_SUPABASE_BUCKET=lumiere-private-photos` and project URL as
   **staging backend** environment variables; do not store them in Expo.
3. Keep the secret only in a privileged backend runtime, never in client
   bundle variables, source control, screenshots or log output.
4. Test two staging accounts end-to-end and the storage deletion cascade
   before activating customer uploads. Plan legacy local/Emergent files as
   a separately authorized migration; do not delete them automatically.
5. Document retention and legal requirements. Supabase's Storage deletion
   documentation describes removal of object bytes via Storage API, but
   does not itself establish erasure from every provider backup or other
   downstream copy.

Sources:
- https://supabase.com/docs/guides/storage/management/delete-objects
- https://supabase.com/docs/guides/storage/cdn/fundamentals
- https://supabase.com/docs/guides/storage/cdn/smart-cdn

## Current staged rollout (October 2026)
1. Intended customer bucket read-only privacy preflight: `bash scripts/verify-customer-bucket.sh`. It fails closed if missing, unreachable or public; requires the existing GitHub Codespaces secret. The successful private **test** bucket verification does not prove the **customer** bucket is private.
2. Backend supports `LUMIERE_PHOTO_STORAGE=supabase` for **new uploads** and still reads/deletes pre-existing `local/<id>.png` images when `LUMIERE_LOCAL_IMAGE_STORAGE=1`. Preserve the Codespaces `backend/.lumiere-private-images` directory. This is not an automatic migration. Startup fails if Supabase bucket privacy cannot be verified.
3. First run a staging instance with the same account database but a separate private port, or explicitly switch the Codespaces backend after step 1, preserving all local image files and database records. Do not change a production deployment or expose a private Codespaces port.
4. The You screen now has a two-tap **Delete this photograph** action for the saved colour analysis photo. It calls the authenticated account API, removes linked analysis/try-on references and refreshes the profile. Test only on a new disposable customer and generated test image, not an existing personal photograph.
5. Before public launch document response to deletion requests, service provider cache retention, internal backup copies and incident response; REST delete+404 does not certify erasure from every backup copy. Official documentation: https://supabase.com/docs/guides/storage/management/delete-objects and https://supabase.com/docs/guides/storage/cdn/fundamentals .
