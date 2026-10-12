"""Opt-in real AI E2E against disposable local-storage Codespaces backend.

Requires two consented/non-sensitive test photos: clear FACE and FULL_BODY.
Creates a fresh disposable account and calls paid ChatGPT/Gemini providers.
Do not run on production or while using undeletable remote object storage.
"""
import os
import secrets
import sys
from pathlib import Path
import requests

BASE = os.environ.get("LUMIERE_LIVE_API_URL", "").rstrip("/")
ACK = os.environ.get("LUMIERE_AI_E2E_ACK", "")
FACE = os.environ.get("LUMIERE_TEST_FACE_IMAGE", "")
BODY = os.environ.get("LUMIERE_TEST_FULL_BODY_IMAGE", "")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def request(method, url, token=None, **kwargs):
    headers = {"Authorization": "Bearer " + token} if token else {}
    res = requests.request(method, BASE + url, headers=headers, timeout=240, **kwargs)
    require(res.status_code < 300, f"{url}: HTTP {res.status_code} ({res.text[:180]})")
    return res


def upload(path, token):
    with open(path, "rb") as stream:
        mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
        result = request("POST", "/api/account/photos", token,
                         files={"file": (Path(path).name, stream, mime)})
    return result.json()["id"]


def main():
    require(ACK == "disposable-local-photos-and-ai-credits", "Explicit test acknowledgement is required")
    require(BASE in ("http://127.0.0.1:8000", "http://localhost:8000"), "Local private backend only")
    require(FACE and BODY and Path(FACE).is_file() and Path(BODY).is_file(), "Two consented test image files required")
    require(all(Path(p).suffix.lower() in (".jpg", ".jpeg", ".png") for p in (FACE, BODY)), "Use JPG/PNG fixtures")
    email = "lumiere-ai-smoke-" + secrets.token_hex(8) + "@example.invalid"
    password = "test-ai-" + secrets.token_urlsafe(24)
    request("POST", "/api/account/register", json={"email": email, "password": password})
    token = request("POST", "/api/account/login", json={"email": email, "password": password}).json()["access_token"]
    photo_ids = []
    try:
        face_id = upload(FACE, token)
        photo_ids.append(face_id)
        body_id = upload(BODY, token)
        photo_ids.append(body_id)
        skin = request("POST", "/api/account/skin-analysis", token,
                       json={"image_path": "private:" + face_id, "provider": "openai"}).json()
        require(skin.get("undertone"), "ChatGPT analysis missing undertone")
        profile = request("GET", "/api/account/profile", token).json()
        require(profile.get("skin", {}).get("image_path") == "private:" + face_id,
                "Skin analysis did not persist to own account")
        conversation = request("POST", "/api/account/conversations", token).json()
        chat = request("POST", f"/api/account/conversations/{conversation['id']}/chat", token,
                       json={"message": "Suggest a breathable warm-weather outfit.", "provider": "openai"}).text
        require('"delta":' in chat and '"done": true' in chat, "ChatGPT styling response missing")
        products = request("GET", "/api/account/catalogue/recommendations", token).json()
        require(isinstance(products, dict), "Authenticated recommendations response malformed")
        tryon = request("POST", "/api/account/tryons", token,
                        json={"person_photo_id": body_id,
                              "garment_prompt": "Lightweight linen shirt and tailored trousers"}).json()
        result_id = tryon.get("result_photo_id")
        require(result_id, "Gemini image result not recorded")
        photo_ids.append(result_id)
        require(request("GET", "/api/account/photos/" + result_id, token).content,
                "Generated Try-On photograph not readable")
        print("PASS: real provider colour analysis, private profile persistence, styling chat, recommendations and Try-On")
        print("NOTE: visual quality, face accuracy, mobile UI, and provider backup retention need independent review")
    finally:
        for photo_id in reversed(photo_ids):
            try:
                requests.delete(BASE + "/api/account/photos/" + photo_id,
                                headers={"Authorization": "Bearer " + token}, timeout=20)
            except Exception:
                pass
        requests.post(BASE + "/api/account/logout",
                      headers={"Authorization": "Bearer " + token}, timeout=15)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
