"""Mocked deletion protocol tests; they do NOT prove live provider retention."""
import io
import os
import pytest
from botocore.exceptions import ClientError

from services import s3_photos


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.versions = {}
        self.deleted_version_ids = []

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = (kwargs["Body"], kwargs["ContentType"])

    def get_object(self, **kwargs):
        if kwargs["Key"] not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        data, mime = self.objects[kwargs["Key"]]
        return {"Body": io.BytesIO(data), "ContentType": mime}

    def list_object_versions(self, **kwargs):
        key = kwargs["Prefix"]
        return {"Versions": [{"Key": key, "VersionId": v}
                             for v in self.versions.get(key, [])],
                "IsTruncated": False}

    def delete_object(self, **kwargs):
        if "VersionId" in kwargs:
            self.deleted_version_ids.append(kwargs["VersionId"])
            self.versions[kwargs["Key"]].remove(kwargs["VersionId"])
        else:
            self.objects.pop(kwargs["Key"], None)

    def head_object(self, **kwargs):
        if kwargs["Key"] in self.objects:
            return {"ContentLength": len(self.objects[kwargs["Key"]][0])}
        raise ClientError({"Error": {"Code": "404"}}, "HeadObject")


@pytest.fixture(autouse=True)
def bucket(monkeypatch):
    monkeypatch.setenv("LUMIERE_S3_BUCKET", "lumiere-disposable-test-bucket")


def test_s3_roundtrip_and_verified_version_deletion():
    fake = FakeS3()
    path = s3_photos.upload(b"synthetic test image", "png", "image/png", s3=fake)
    assert path.startswith("s3private:lumiere/private/")
    assert s3_photos.read(path, s3=fake)[0] == b"synthetic test image"
    key = path.removeprefix("s3private:")
    fake.versions[key] = ["older", "newer"]
    s3_photos.delete_verified(path, s3=fake)
    assert fake.deleted_version_ids == ["older", "newer"]
    with pytest.raises(ClientError):
        s3_photos.read(path, s3=fake)


def test_s3_rejects_external_paths_and_invalid_uploads():
    fake = FakeS3()
    for path in ("s3private:../elsewhere", "stylescan/uploads/anon/abc.png",
                 "s3private:lumiere/private/../../secret.jpg"):
        with pytest.raises(ValueError):
            s3_photos.delete_verified(path, s3=fake)
    with pytest.raises(ValueError):
        s3_photos.upload(b"image", "exe", "text/plain", s3=fake)


def test_s3_deletion_failure_must_not_report_success():
    fake = FakeS3()
    path = s3_photos.upload(b"fake image", "jpg", "image/jpeg", s3=fake)
    fake.delete_object = lambda **kwargs: None
    with pytest.raises(RuntimeError, match="remains readable"):
        s3_photos.delete_verified(path, s3=fake)
