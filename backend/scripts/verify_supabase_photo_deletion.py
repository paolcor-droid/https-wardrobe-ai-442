"""Opt-in test against an isolated Supabase project with a PRIVATE test bucket.

Creates, reads and deletes a synthetic PNG. Do not run against a production
project; does not establish provider backup/retention erasure.
"""
import io
import os
import sys
from PIL import Image
from services import supabase_photos

def main():
    if os.environ.get("LUMIERE_SUPABASE_TEST_ACK") != "delete-synthetic-test-image":
        raise RuntimeError("Explicit disposable storage test acknowledgement required")
    _, _, bucket = supabase_photos.settings()
    expected = os.environ.get("LUMIERE_SUPABASE_TEST_BUCKET", "")
    if bucket != expected or "test" not in bucket.lower():
        raise RuntimeError("Require matching dedicated test bucket name containing 'test'")
    image = io.BytesIO()
    Image.new("RGB", (16, 16), color=(75, 125, 175)).save(image, "PNG")
    path = supabase_photos.upload(image.getvalue(), "png", "image/png")
    try:
        assert supabase_photos.read(path)[0] == image.getvalue(), "Test image read-back mismatch"
        supabase_photos.delete_verified(path)
        print("PASS: synthetic test photo uploaded, authenticated read verified, DELETE acknowledged and authenticated read-back absent")
        print("NOT PROVEN: storage-provider internal copies, backups, CDN expiration or physical retention")
    finally:
        # Best-effort cleanup of a disposable test image only.
        try:
            supabase_photos.delete_verified(path)
        except Exception:
            pass

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
