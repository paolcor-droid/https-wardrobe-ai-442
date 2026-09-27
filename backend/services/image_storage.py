"""Image storage boundary for StyleScan v2.

The current MVP still accepts legacy base64 fields. New deployments can configure
S3-compatible object storage without coupling API routes to a vendor.
"""
from __future__ import annotations
import base64, os, uuid
from dataclasses import dataclass
import boto3

@dataclass
class StoredImage:
    key: str
    url: str

class ImageStorage:
    def __init__(self):
        self.bucket = os.getenv("IMAGE_BUCKET")
        self.public_base = os.getenv("IMAGE_PUBLIC_BASE_URL", "").rstrip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=os.getenv("IMAGE_S3_ENDPOINT") or None,
            region_name=os.getenv("IMAGE_S3_REGION") or None,
            aws_access_key_id=os.getenv("IMAGE_S3_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("IMAGE_S3_SECRET_ACCESS_KEY") or None,
        ) if self.bucket else None

    @property
    def configured(self) -> bool:
        return bool(self.client and self.bucket and self.public_base)

    def put_base64(self, payload: str, folder: str, content_type: str = "image/jpeg") -> StoredImage:
        if not self.configured:
            raise RuntimeError("Object storage is not configured")
        raw = payload.split(",", 1)[-1]
        data = base64.b64decode(raw)
        ext = "png" if content_type == "image/png" else "jpg"
        key = f"{folder}/{uuid.uuid4()}.{ext}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return StoredImage(key=key, url=f"{self.public_base}/{key}")
