"""Backend tests for StyleScan Claude Sonnet 5 chat integration."""
import json
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else None

# Fallback to reading from frontend/.env if not set in env
if not BASE_URL:
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def convo_id():
    r = requests.post(f"{API}/conversations", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "id" in d and isinstance(d["id"], str)
    # id should be a valid UUID string, not Mongo ObjectId
    uuid.UUID(d["id"])
    assert "_id" not in d
    assert d["title"] == "New styling session"
    return d["id"]


# ---------- Conversation CRUD ----------
class TestConversationCRUD:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        assert r.json().get("message") == "StyleScan API"

    def test_create_and_list(self, convo_id):
        r = requests.get(f"{API}/conversations", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        ids = [c["id"] for c in items]
        assert convo_id in ids
        # No _id leakage
        for c in items:
            assert "_id" not in c
            assert "id" in c and "title" in c and "updated_at" in c

    def test_list_sorted_desc(self, convo_id):
        # Create another convo and confirm it comes first (updated_at desc)
        r = requests.post(f"{API}/conversations", timeout=15)
        assert r.status_code == 200
        newer = r.json()["id"]
        time.sleep(0.2)
        items = requests.get(f"{API}/conversations", timeout=15).json()
        # newer must appear before older convo_id
        idx_new = next(i for i, c in enumerate(items) if c["id"] == newer)
        idx_old = next(i for i, c in enumerate(items) if c["id"] == convo_id)
        assert idx_new < idx_old
        # cleanup
        requests.delete(f"{API}/conversations/{newer}", timeout=15)

    def test_messages_empty_initially(self, convo_id):
        r = requests.get(f"{API}/conversations/{convo_id}/messages", timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_404_on_bad_id(self):
        bad = str(uuid.uuid4())
        r = requests.get(f"{API}/conversations/{bad}/messages", timeout=15)
        assert r.status_code == 404
        r = requests.post(f"{API}/conversations/{bad}/chat", json={"message": "hi"}, timeout=15)
        assert r.status_code == 404
        r = requests.delete(f"{API}/conversations/{bad}", timeout=15)
        assert r.status_code == 404


def _stream_chat(convo_id, message, timeout=90):
    """Consume the SSE stream and return (deltas, done_payload, errors)."""
    deltas = []
    done = None
    errors = []
    with requests.post(
        f"{API}/conversations/{convo_id}/chat",
        json={"message": message},
        stream=True,
        timeout=timeout,
    ) as r:
        assert r.status_code == 200, r.text
        assert "text/event-stream" in r.headers.get("content-type", "")
        buffer = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buffer += chunk
            while "\n\n" in buffer:
                raw, buffer = buffer.split("\n\n", 1)
                line = raw.strip()
                if not line.startswith("data:"):
                    continue
                data = json.loads(line[5:].strip())
                if "delta" in data:
                    deltas.append(data["delta"])
                elif data.get("done"):
                    done = data
                elif "error" in data:
                    errors.append(data["error"])
            if done:
                break
    return deltas, done, errors


# ---------- Chat streaming ----------
class TestChatStreaming:
    def test_stream_first_message_sets_title(self, convo_id):
        deltas, done, errors = _stream_chat(
            convo_id, "In one short sentence, name three neutral colors for a capsule wardrobe."
        )
        assert not errors, f"errors: {errors}"
        assert len(deltas) >= 1, "expected at least one token delta"
        full = "".join(deltas).strip()
        assert len(full) > 5
        assert done is not None
        assert done.get("message_id")
        # Title should have been set from the first user message
        assert done.get("title")

        # Verify persistence
        msgs = requests.get(f"{API}/conversations/{convo_id}/messages", timeout=15).json()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"].strip() == full

        # Verify title updated on conversation
        conv = next(
            c for c in requests.get(f"{API}/conversations", timeout=15).json()
            if c["id"] == convo_id
        )
        assert conv["title"] != "New styling session"

    def test_multi_turn_context(self, convo_id):
        # Set an anchor fact in a fresh convo
        r = requests.post(f"{API}/conversations", timeout=15)
        cid = r.json()["id"]
        _, done1, err1 = _stream_chat(
            cid, "Please remember my favorite color is emerald green. Reply with just OK."
        )
        assert not err1 and done1

        # Ask follow-up
        deltas2, done2, err2 = _stream_chat(cid, "What is my favorite color? Answer in one word.")
        assert not err2 and done2
        answer = "".join(deltas2).lower()
        assert "emerald" in answer or "green" in answer, f"context lost: {answer!r}"

        # cleanup
        requests.delete(f"{API}/conversations/{cid}", timeout=15)

    def test_empty_message_rejected(self, convo_id):
        r = requests.post(
            f"{API}/conversations/{convo_id}/chat", json={"message": "   "}, timeout=15
        )
        assert r.status_code == 400


# ---------- Delete ----------
class TestDelete:
    def test_soft_delete_hides_from_list(self):
        cid = requests.post(f"{API}/conversations", timeout=15).json()["id"]
        assert any(c["id"] == cid for c in requests.get(f"{API}/conversations", timeout=15).json())
        r = requests.delete(f"{API}/conversations/{cid}", timeout=15)
        assert r.status_code == 200 and r.json().get("success") is True
        items = requests.get(f"{API}/conversations", timeout=15).json()
        assert not any(c["id"] == cid for c in items)
        # Messages endpoint should now 404 (deleted_at filter)
        r = requests.get(f"{API}/conversations/{cid}/messages", timeout=15)
        assert r.status_code == 404
