"""Private S3 photograph storage with strict key validation and deletion readback.

Requires separately configured LUMIERE_S3_BUCKET and AWS IAM credentials.
Does not guarantee purge of external backups/CDN or providers' retention systems.
"""
import io
import os
import re
import uuid

_PREFIX = "lumiere/private/"
_PATTERN = re.compile(r"lumiere/private/[0-9a-f]{32}\.(?:jpg|jpeg|png|webp)\Z")


def validate_key(key: str) -> str:
    if not _PATTERN.fullmatch(key):
        raise ValueError("Invalid LUMIÈRE S3 image key")
    return key


def bucket() -> str:
    name = os.environ.get("LUMIERE_S3_BUCKET", "").strip()
    if not name or "/" in name:
        raise RuntimeError("Private S3 bucket is not configured")
    return name


def client():
    import boto3
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION") or None)


def upload(data: bytes, ext: str, mime: str, s3=None) -> str:
    if ext not in ("jpg", "jpeg", "png", "webp") or len(data) > 8 * 1024 * 1024:
        raise ValueError("Invalid private photograph")
    key = _PREFIX + uuid.uuid4().hex + "." + ext
    c = s3 or client()
    c.put_object(Bucket=bucket(), Key=key, Body=data, ContentType=mime,
                 ServerSideEncryption="AES256", CacheControl="private, no-store")
    return "s3private:" + key


def read(path: str, s3=None) -> tuple[bytes, str]:
    if not path.startswith("s3private:"):
        raise ValueError("Invalid private S3 path")
    key = validate_key(path.removeprefix("s3private:"))
    obj = (s3 or client()).get_object(Bucket=bucket(), Key=key)
    return obj["Body"].read(), obj.get("ContentType") or "application/octet-stream"


def delete_verified(path: str, s3=None) -> None:
    """Delete current object and every listed version, then require no readable current object.

    A bucket with legal holds, Object Lock, or insufficient version permissions must
    fail rather than remove its account metadata. Provider backups require independent review.
    """
    from botocore.exceptions import ClientError
    if not path.startswith("s3private:"):
        raise ValueError("Invalid private S3 path")
    key = validate_key(path.removeprefix("s3private:"))
    c = s3 or client()
    name = bucket()
    # Remove all versions first, so versioning cannot silently retain face photos.
    marker = None
    version_marker = None
    while True:
        kwargs = {"Bucket": name, "Prefix": key}
        if marker:
            kwargs["KeyMarker"] = marker
        if version_marker:
            kwargs["VersionIdMarker"] = version_marker
        page = c.list_object_versions(**kwargs)
        versions = [v for kind in ("Versions", "DeleteMarkers")
                    for v in page.get(kind, []) if v.get("Key") == key]
        for version in versions:
            c.delete_object(Bucket=name, Key=key, VersionId=version["VersionId"])
        if not page.get("IsTruncated"):
            break
        marker = page.get("NextKeyMarker")
        version_marker = page.get("NextVersionIdMarker")
        if not marker:
            raise RuntimeError("S3 version listing could not be completed")
    c.delete_object(Bucket=name, Key=key)
    try:
        c.head_object(Bucket=name, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchKey", "NotFound"):
            return
        raise
    raise RuntimeError("S3 photograph remains readable after deletion")
