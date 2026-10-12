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
