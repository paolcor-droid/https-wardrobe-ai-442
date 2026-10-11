import pytest
from services.remote_photo_deletion import delete_and_verify_remote

PATH = "stylescan/uploads/anon/" + "a" * 32 + ".png"


class Reply:
    def __init__(self, status_code):
        self.status_code = status_code


def test_remote_deletion_requires_delete_ack_and_404_readback():
    calls = []
    def remove(url, **kwargs):
        calls.append(("delete", url, kwargs))
        return Reply(204)
    def read(url, **kwargs):
        calls.append(("get", url, kwargs))
        return Reply(404)
    assert delete_and_verify_remote(PATH, "https://storage.example", "storage-key", remove, read)
    assert [call[0] for call in calls] == ["delete", "get"]
    assert calls[0][1] == calls[1][1]
    assert calls[0][2]["headers"] == {"X-Storage-Key": "storage-key"}


def test_remote_deletion_fails_when_object_still_accessible():
    with pytest.raises(RuntimeError):
        delete_and_verify_remote(
            PATH, "https://storage.example", "key",
            lambda *a, **k: Reply(200),
            lambda *a, **k: Reply(200),
        )


def test_remote_deletion_fails_on_unrecognised_provider_response():
    with pytest.raises(RuntimeError):
        delete_and_verify_remote(
            PATH, "https://storage.example", "key",
            lambda *a, **k: Reply(405),
            lambda *a, **k: pytest.fail("must not attempt unacknowledged read-back"),
        )


def test_remote_deletion_rejects_untrusted_paths_before_any_network_call():
    for path in ("../../secrets", "https://evil.example/photo.jpg", "local/other.png"):
        with pytest.raises(ValueError):
            delete_and_verify_remote(
                path, "https://storage.example", "key",
                lambda *a, **k: pytest.fail("unexpected delete"),
                lambda *a, **k: pytest.fail("unexpected read"),
            )
