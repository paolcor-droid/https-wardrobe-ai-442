"""Verification gate for private object-store deletion.

The provider's DELETE support must be validated with real deployed credentials
before enabling LUMIERE_REMOTE_DELETE_ENABLED. Unit tests alone are insufficient.
"""
import re


def delete_and_verify_remote(path, storage_url, key, http_delete, http_get):
    if not re.fullmatch(
        r"stylescan/uploads/anon/(?:[0-9a-f]{32}|"
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        r"\.(?:jpg|jpeg|png|webp)", path,
    ):
        raise ValueError("Invalid remote photo path")
    endpoint = f"{storage_url.rstrip('/')}/objects/{path}"
    headers = {"X-Storage-Key": key}
    deleted = http_delete(endpoint, headers=headers, timeout=60)
    if deleted.status_code not in (200, 202, 204, 404):
        raise RuntimeError(f"Object deletion failed ({deleted.status_code})")
    verify = http_get(endpoint, headers=headers, timeout=60)
    if verify.status_code != 404:
        raise RuntimeError("Remote deletion cannot be confirmed by read-back")
    return True
