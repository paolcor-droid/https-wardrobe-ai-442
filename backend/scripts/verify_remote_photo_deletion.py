"""Opt-in destructive verification of remote photograph deletion on a dedicated TEST object.

This script does not create an object and refuses to delete arbitrary keys.
Upload a disposable test image via the provider console first and supply its
exact key. The test confirms DELETE+404 read-back, NOT physical purge from
backups, caches, replicas, or retention systems.
"""
import os
import sys
import requests
from services.remote_photo_deletion import delete_and_verify_remote

def main():
    if os.environ.get("LUMIERE_DELETION_TEST_ACK") != "delete-disposable-object":
        raise SystemExit("Set LUMIERE_DELETION_TEST_ACK=delete-disposable-object")
    key = os.environ.get("LUMIERE_DELETION_TEST_OBJECT", "")
    url = os.environ.get("LUMIERE_STORAGE_TEST_URL", "")
    secret = os.environ.get("LUMIERE_STORAGE_TEST_KEY", "")
    if not (key and url.startswith("https://") and secret):
        raise SystemExit("Need dedicated HTTPS test storage URL, test key, and disposable image key")
    # Explicit opt-in allowlist: never use a production storage base accidentally.
    if os.environ.get("LUMIERE_STORAGE_TEST_ISOLATED") != "yes":
        raise SystemExit("Must confirm isolated, non-production storage environment")
    # Prevent treating a preexisting missing object as a successful deletion.
    endpoint = url.rstrip("/") + "/objects/" + key
    pre = requests.get(endpoint, headers={"X-Storage-Key": secret}, timeout=30)
    if pre.status_code != 200:
        raise RuntimeError(f"Dedicated test object must be readable before deletion (HTTP {pre.status_code})")
    delete_and_verify_remote(key, url, secret, requests.delete, requests.get)
    print("PASS: dedicated remote test object DELETE acknowledged and authenticated GET returned 404")
    print("NOT verified: backup retention, replicas, CDN, provider physical purge, and production-account deletion")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
