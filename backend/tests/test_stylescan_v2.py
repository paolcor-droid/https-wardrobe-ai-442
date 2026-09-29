"""Backend tests for StyleScan v2 features:
- Photo upload + file fetch (Emergent Object Storage)
- Chat with image_path (Claude vision) — persist image_path on user message
- Rename + pin conversations (PATCH) with pinned-first ordering
- Saved looks: create (idempotent), list, delete (soft)
"""
import io
import json
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"')
                break
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


# ---- helpers ----
def _make_png_bytes(color=(139, 69, 19)):
    """Tiny 8x8 solid-color PNG (brown by default)."""
    import struct, zlib
    w = h = 8
    raw = b"".join(b"\x00" + bytes(color) * w for _ in range(h))

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _stream_chat(convo_id, message, image_path=None, timeout=120):
    deltas, done, errors = [], None, []
    with requests.post(
        f"{API}/conversations/{convo_id}/chat",
        json={"message": message, "image_path": image_path},
        stream=True,
        timeout=timeout,
    ) as r:
        assert r.status_code == 200, r.text
        buf = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                line = raw.strip()
                if not line.startswith("data:"):
                    continue
                d = json.loads(line[5:].strip())
                if "delta" in d:
                    deltas.append(d["delta"])
                elif d.get("done"):
                    done = d
                elif "error" in d:
                    errors.append(d["error"])
            if done:
                break
    return deltas, done, errors


# ---------- Upload + Files ----------
class TestUploadFiles:
    def test_upload_returns_path(self):
        png = _make_png_bytes()
        files = {"file": ("swatch.png", io.BytesIO(png), "image/png")}
        r = requests.post(f"{API}/upload", files=files, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "path" in body and isinstance(body["path"], str) and body["path"]
        assert body["path"].startswith("stylescan/uploads/")
        pytest.upload_path = body["path"]
        pytest.upload_bytes = png

    def test_fetch_file_returns_bytes(self):
        path = getattr(pytest, "upload_path", None)
        assert path, "upload did not run"
        r = requests.get(f"{API}/files/{path}", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        # Body should be non-empty; ideally match uploaded bytes
        assert len(r.content) > 0
        # Best-effort byte match (object storage should return exact bytes)
        assert r.content == pytest.upload_bytes

    def test_fetch_missing_file_404(self):
        r = requests.get(f"{API}/files/stylescan/uploads/anon/{uuid.uuid4()}.png", timeout=30)
        assert r.status_code == 404


# ---------- Chat with image (vision) ----------
class TestChatVision:
    def test_chat_with_image_path_persists_and_describes(self):
        # Upload a brown swatch
        png = _make_png_bytes(color=(101, 67, 33))
        r = requests.post(
            f"{API}/upload",
            files={"file": ("brown.png", io.BytesIO(png), "image/png")},
            timeout=60,
        )
        assert r.status_code == 200
        path = r.json()["path"]

        # Create a fresh conversation
        cid = requests.post(f"{API}/conversations", timeout=15).json()["id"]

        deltas, done, errors = _stream_chat(
            cid,
            "In one short sentence, name the dominant color in this image.",
            image_path=path,
        )
        assert not errors, f"errors: {errors}"
        assert done and done.get("message_id")
        text = "".join(deltas).lower()
        assert any(
            kw in text
            for kw in ("brown", "espresso", "chocolate", "coffee", "tan", "sepia", "mocha")
        ), f"vision did not identify brown-ish color: {text!r}"

        # Verify the user message stored image_path
        msgs = requests.get(f"{API}/conversations/{cid}/messages", timeout=15).json()
        assert len(msgs) == 2
        user = msgs[0]
        assert user["role"] == "user"
        assert user["image_path"] == path
        assert msgs[1]["role"] == "assistant"

        # cleanup
        requests.delete(f"{API}/conversations/{cid}", timeout=15)


# ---------- Rename + Pin ----------
class TestRenamePin:
    def test_patch_rename_and_pin_and_ordering(self):
        # create A (older) and B (newer)
        a = requests.post(f"{API}/conversations", timeout=15).json()["id"]
        time.sleep(0.3)
        b = requests.post(f"{API}/conversations", timeout=15).json()["id"]

        # rename A
        r = requests.patch(f"{API}/conversations/{a}", json={"title": "  Paris Trip  "}, timeout=15)
        assert r.status_code == 200
        assert r.json()["title"] == "Paris Trip"
        assert r.json()["pinned"] is False

        # pin A
        r = requests.patch(f"{API}/conversations/{a}", json={"pinned": True}, timeout=15)
        assert r.status_code == 200 and r.json()["pinned"] is True

        # list: A (pinned) must come before B (newer but unpinned)
        items = requests.get(f"{API}/conversations", timeout=15).json()
        idx_a = next(i for i, c in enumerate(items) if c["id"] == a)
        idx_b = next(i for i, c in enumerate(items) if c["id"] == b)
        assert idx_a < idx_b, "pinned convo should sort before unpinned newer one"

        # unpin A: B should come before A now (B is newer)
        requests.patch(f"{API}/conversations/{a}", json={"pinned": False}, timeout=15)
        items = requests.get(f"{API}/conversations", timeout=15).json()
        idx_a = next(i for i, c in enumerate(items) if c["id"] == a)
        idx_b = next(i for i, c in enumerate(items) if c["id"] == b)
        assert idx_b < idx_a

        # empty body -> 400
        r = requests.patch(f"{API}/conversations/{a}", json={}, timeout=15)
        assert r.status_code == 400

        # bad id -> 404
        r = requests.patch(
            f"{API}/conversations/{uuid.uuid4()}", json={"pinned": True}, timeout=15
        )
        assert r.status_code == 404

        # cleanup
        requests.delete(f"{API}/conversations/{a}", timeout=15)
        requests.delete(f"{API}/conversations/{b}", timeout=15)

    def test_title_trimmed_to_60_chars(self):
        cid = requests.post(f"{API}/conversations", timeout=15).json()["id"]
        long_title = "x" * 80
        r = requests.patch(f"{API}/conversations/{cid}", json={"title": long_title}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["title"]) == 60
        requests.delete(f"{API}/conversations/{cid}", timeout=15)


# ---------- Saved looks ----------
class TestSavedLooks:
    @pytest.fixture(scope="class")
    def message_id(self):
        # need a real assistant message id — stream one
        cid = requests.post(f"{API}/conversations", timeout=15).json()["id"]
        _, done, errors = _stream_chat(cid, "Say hi in one word.")
        assert not errors and done
        pytest.saved_cid = cid
        return done["message_id"]

    def test_save_creates_look(self, message_id):
        r = requests.post(f"{API}/saved", json={"message_id": message_id}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["message_id"] == message_id
        assert data["conversation_id"] == pytest.saved_cid
        assert data["content"]
        pytest.saved_id = data["id"]

    def test_save_is_idempotent(self, message_id):
        r = requests.post(f"{API}/saved", json={"message_id": message_id}, timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == pytest.saved_id, "saving same message twice must return same look"

    def test_save_bad_message_id_404(self):
        r = requests.post(
            f"{API}/saved", json={"message_id": str(uuid.uuid4())}, timeout=15
        )
        assert r.status_code == 404

    def test_list_saved(self, message_id):
        r = requests.get(f"{API}/saved", timeout=15)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert pytest.saved_id in ids
        for x in r.json():
            assert "_id" not in x

    def test_delete_saved_removes_from_list(self):
        r = requests.delete(f"{API}/saved/{pytest.saved_id}", timeout=15)
        assert r.status_code == 200 and r.json().get("success") is True
        ids = [x["id"] for x in requests.get(f"{API}/saved", timeout=15).json()]
        assert pytest.saved_id not in ids
        # deleting again -> 404
        r = requests.delete(f"{API}/saved/{pytest.saved_id}", timeout=15)
        assert r.status_code == 404
        # cleanup conversation
        requests.delete(f"{API}/conversations/{pytest.saved_cid}", timeout=15)
