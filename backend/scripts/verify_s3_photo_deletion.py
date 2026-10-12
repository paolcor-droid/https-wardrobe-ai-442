"""Destructive, opt-in live verification in an isolated disposable S3 TEST bucket.

Not proof of deletion from AWS backups, replicas, legal holds, or external CDN.
AWS credentials must be injected as environment/role, never printed or committed.
"""
import io
import os
import sys
from PIL import Image
from services import s3_photos


def main():
    bucket = os.environ.get("LUMIERE_S3_BUCKET", "")
    confirmation = os.environ.get("LUMIERE_S3_TEST_BUCKET", "")
    if os.environ.get("LUMIERE_S3_TEST_ACK") != "delete-disposable-photo":
        raise RuntimeError("Refusing S3 write/delete without test acknowledgement")
    if not bucket or bucket != confirmation or not any(x in bucket.lower() for x in ("test", "sandbox", "dev")):
        raise RuntimeError("Use a separately named, matching disposable TEST bucket")
    result = io.BytesIO()
    Image.new("RGB", (16, 16), color=(70, 120, 180)).save(result, "PNG")
    path = s3_photos.upload(result.getvalue(), "png", "image/png")
    try:
        assert s3_photos.read(path)[0] == result.getvalue()
        s3_photos.delete_verified(path)
        c = s3_photos.client()
        key = s3_photos.validate_key(path.removeprefix("s3private:"))
        page = c.list_object_versions(Bucket=bucket, Prefix=key)
        remaining = [
            v for kind in ("Versions", "DeleteMarkers")
            for v in page.get(kind, []) if v.get("Key") == key
        ]
        if remaining:
            raise RuntimeError("Photo versions or delete markers remain")
        print("PASS: disposable S3 test object uploaded, read, deleted; HEAD returned 404; no listed versions remain")
        print("NOT PROVEN: S3/provider backup rotation, replication, CDN caching, legal retention, downstream copies")
    finally:
        # Best-effort cleanup if an intermediate assertion fails. Never mask the original error.
        try:
            s3_photos.delete_verified(path)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL:", type(error).__name__, str(error), file=sys.stderr)
        sys.exit(1)
