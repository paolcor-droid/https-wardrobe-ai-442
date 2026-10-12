"""Mocked Supabase transport tests: never use customer photos or remote credentials."""
import pytest
from services import supabase_photos

class Response:
    def __init__(self, status, content=b"", mime="image/png"):
        self.status_code=status
        self.content=content
        self.headers={"Content-Type": mime}

class FakeHTTP:
    def __init__(self):
        self.objects={}
    def post(self, url, headers, data, timeout):
        self.objects[url]=data
        return Response(200)
    def get(self, url, headers, timeout):
        url=url.replace("/object/authenticated/", "/object/")
        return Response(200, self.objects[url]) if url in self.objects else Response(404)
    def delete(self, url, headers, timeout):
        return Response(200 if self.objects.pop(url,None) is not None else 404)

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LUMIERE_SUPABASE_URL", "https://unit-test.supabase.co")
    monkeypatch.setenv("LUMIERE_SUPABASE_SERVICE_ROLE_KEY", "mock-server-key")
    monkeypatch.setenv("LUMIERE_SUPABASE_BUCKET", "lumiere-private-photos")


def test_private_storage_upload_read_delete_and_missing_readback():
    http=FakeHTTP()
    path=supabase_photos.upload(b"synthetic", "png", "image/png", http=http)
    assert path.startswith("supabaseprivate:lumiere/private/")
    assert supabase_photos.read(path, http=http)[0] == b"synthetic"
    supabase_photos.delete_verified(path, http=http)
    with pytest.raises(RuntimeError):
        supabase_photos.read(path, http=http)


def test_invalid_keys_or_provider_failure_fail_closed():
    http=FakeHTTP()
    for path in ("supabaseprivate:../../sensitive.jpg", "https://example.com/any.jpg"):
        with pytest.raises(ValueError):
            supabase_photos.delete_verified(path, http=http)
    with pytest.raises(ValueError):
        supabase_photos.upload(b"data", "exe", "application/octet-stream", http=http)
    with pytest.raises(RuntimeError):
        supabase_photos.delete_verified("supabaseprivate:lumiere/private/" + "a"*32 + ".png", http=http)


def test_requires_https_and_secret(monkeypatch):
    monkeypatch.setenv("LUMIERE_SUPABASE_URL", "http://bad.example")
    with pytest.raises(RuntimeError):
        supabase_photos.settings()
    monkeypatch.setenv("LUMIERE_SUPABASE_URL", "https://unit-test.supabase.co")
    monkeypatch.delenv("LUMIERE_SUPABASE_SERVICE_ROLE_KEY")
    with pytest.raises(RuntimeError):
        supabase_photos.settings()


def test_private_bucket_guard_fails_closed(monkeypatch):
    class Probe:
        def __init__(self, public): self.public = public
        def get(self, url, headers, timeout):
            assert url.endswith("/storage/v1/bucket/lumiere-private-photos")
            class Result:
                status_code = 200
                def json(inner): return {"public": self.public}
            return Result()
    assert supabase_photos.verify_private_bucket(http=Probe(False))
    with pytest.raises(RuntimeError, match="must be private"):
        supabase_photos.verify_private_bucket(http=Probe(True))
