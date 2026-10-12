"""Server-only private Supabase Storage adapter.

Never expose the Supabase service-role key to mobile/web clients. FastAPI
validates ownership before reading or deleting photographs.
Storage deletion/404 is NOT proof of physical backup purge.
"""
import os
import re
import uuid
from urllib.parse import quote, urlsplit
import requests

_RE = re.compile(r"lumiere/private/[0-9a-f]{32}\.(?:jpg|jpeg|png|webp)\Z")


def settings():
    url = os.environ.get("LUMIERE_SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("LUMIERE_SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.environ.get("LUMIERE_SUPABASE_BUCKET", "lumiere-private-photos")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path:
        raise RuntimeError("Configure the HTTPS Supabase project URL")
    if not key:
        raise RuntimeError("Supabase server-only service role key is missing")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,62}", bucket):
        raise RuntimeError("Invalid private bucket name")
    return url, key, bucket


def headers(key, mime=None):
    result = {"apikey": key, "Authorization": "Bearer " + key}
    if mime:
        result.update({"Content-Type": mime, "Cache-Control": "no-store", "x-upsert": "false"})
    return result


def object_url(url, bucket, path):
    if not _RE.fullmatch(path):
        raise ValueError("Invalid private photograph path")
    return url + "/storage/v1/object/" + quote(bucket, safe="") + "/" + quote(path, safe="/")


def upload(data, ext, mime, http=None):
    if ext not in ("jpg", "jpeg", "png", "webp") or not data or len(data) > 8 * 1024 * 1024:
        raise ValueError("Invalid photograph payload")
    url, key, bucket = settings()
    path = "lumiere/private/" + uuid.uuid4().hex + "." + ext
    response = (http or requests).post(object_url(url, bucket, path), headers=headers(key, mime), data=data, timeout=45)
    if response.status_code not in (200, 201):
        raise RuntimeError("Private photograph upload failed")
    return "supabaseprivate:" + path


def read(path, http=None):
    url, key, bucket = settings()
    if not path.startswith("supabaseprivate:"):
        raise ValueError("Invalid Supabase path")
    object_url(url, bucket, path.removeprefix("supabaseprivate:"))
    result = (http or requests).get(url + "/storage/v1/object/authenticated/" + quote(bucket, safe="") + "/" + quote(path.removeprefix("supabaseprivate:"), safe="/"),
                                    headers=headers(key), timeout=45)
    if result.status_code != 200:
        raise RuntimeError("Private photograph unavailable")
    return result.content, result.headers.get("Content-Type", "application/octet-stream")


def delete_verified(path, http=None):
    url, key, bucket = settings()
    if not path.startswith("supabaseprivate:"):
        raise ValueError("Invalid Supabase path")
    address = object_url(url, bucket, path.removeprefix("supabaseprivate:"))
    session = http or requests
    response = session.delete(address, headers=headers(key), timeout=45)
    if response.status_code not in (200, 204):
        raise RuntimeError("Storage deletion was not acknowledged")
    readback = session.get(
        url + "/storage/v1/object/authenticated/" + quote(bucket, safe="") + "/" + quote(path.removeprefix("supabaseprivate:"), safe="/"),
        headers=headers(key), timeout=45,
    )
    if readback.status_code == 404:
        return
    if readback.status_code == 400:
        # Some Supabase Storage versions report a missing object as 400.
        # Accept only an explicit not-found payload, never an arbitrary 400.
        body = readback.text.lower() if hasattr(readback, "text") else ""
        if "not found" in body or "not_found" in body or "no such object" in body:
            return
    raise RuntimeError("Deleted object still accessible or deletion unverified")


def verify_private_bucket(http=None):
    """Require the configured bucket to be private before accepting uploads."""
    url, key, bucket = settings()
    response = (http or requests).get(
        url + "/storage/v1/bucket/" + quote(bucket, safe=""),
        headers=headers(key), timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError("Supabase bucket privacy check failed")
    try:
        details = response.json()
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Supabase bucket configuration unreadable") from exc
    if details.get("public") is not False:
        raise RuntimeError("Supabase photo bucket must be private")
    return True
