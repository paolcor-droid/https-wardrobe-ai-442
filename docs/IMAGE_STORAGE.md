# StyleScan v2 image storage

The MVP currently stores body photos and generated try-ons as base64 in MongoDB for backwards compatibility. This must not be the long-term persistence model.

## Target architecture
MongoDB stores only metadata and object references. Face/body/generated images live in S3-compatible object storage. The API returns image URLs.

The adapter is in `backend/services/image_storage.py` and is provider-neutral. Configure:
- IMAGE_BUCKET
- IMAGE_PUBLIC_BASE_URL
- IMAGE_S3_ENDPOINT (optional for AWS S3; set for compatible providers)
- IMAGE_S3_REGION
- IMAGE_S3_ACCESS_KEY_ID
- IMAGE_S3_SECRET_ACCESS_KEY

## Migration sequence
1. Keep legacy base64 reads working.
2. On new uploads, write object storage and persist `body_photo_url/body_photo_key`.
3. Update frontend to prefer URL, with base64 fallback.
4. Migrate existing MongoDB image blobs.
5. Move generated try-ons to object storage.
6. Remove base64 persistence only after migration verification.

This staged migration prevents breaking existing Emergent data while removing large image blobs from MongoDB.
