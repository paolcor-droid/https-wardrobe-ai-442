"""Opt-in smoke test against a RUNNING backend and disposable MongoDB.

Usage (in a private test environment ONLY):
 LUMIERE_LIVE_TEST_ACK=disposable-database LUMIERE_LIVE_API_URL=http://127.0.0.1:8000 \\
     python backend/scripts/live_account_smoke.py

This creates two real accounts (therefore requires a disposable test database). No
provider credentials or login tokens are printed. Does not alter production settings.
"""
import json
import io
from PIL import Image
import os
import secrets
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("LUMIERE_LIVE_API_URL", "").rstrip("/")
if os.environ.get("LUMIERE_LIVE_TEST_ACK") != "disposable-database" or not BASE.startswith(("http://127.0.0.1:", "http://localhost:")):
    raise SystemExit("Refusing: use disposable-database acknowledgement and local backend URL")

def request(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + "/api/account" + path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        return exc.code, None

def upload_test_photo(token):
    # Generated in memory; never uploads a real person's photograph.
    out = io.BytesIO()
    Image.new("RGB", (16, 16), (128, 142, 158)).save(out, format="PNG")
    boundary = "lumiere" + secrets.token_hex(12)
    payload = (("--" + boundary + "\\r\\n"
        'Content-Disposition: form-data; name="file"; filename="test.png"\\r\\n'
        "Content-Type: image/png\\r\\n\\r\\n").encode()
        + out.getvalue() + ("\\r\\n--" + boundary + "--\\r\\n").encode())
    req = urllib.request.Request(
        BASE + "/api/account/photos", data=payload, method="POST",
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary,
                 "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)["id"]

def photo_status(photo_id, token, method="GET"):
    req = urllib.request.Request(
        BASE + "/api/account/photos/" + photo_id, method=method,
        headers={"Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code

def require(value, message):
    if not value:
        raise AssertionError(message)

def main():
    users = []
    for n in range(2):
        email = "lumiere-live-" + secrets.token_hex(8) + "@example.invalid"
        password = "Smoke-" + secrets.token_urlsafe(24)
        status, _ = request("POST", "/register", {"email": email, "password": password})
        require(status == 201, "Registration failed; ensure localhost backend and disposable MongoDB")
        status, data = request("POST", "/login", {"email": email, "password": password})
        require(status == 200 and data and data.get("access_token"), "Login failed")
        users.append(data["access_token"])
    a, b = users
    require(request("GET", "/me", token=a)[0] == 200, "Account A session failed")
    require(request("GET", "/me", token=b)[0] == 200, "Account B session failed")
    status, _ = request("PUT", "/profile", {"notes": "private smoke A"}, a)
    require(status == 200, "Profile write failed")
    status_b, profile_b = request("GET", "/profile", token=b)
    require(status_b == 200 and isinstance(profile_b, dict), "Profile B read failed")
    require(profile_b.get("notes") != "private smoke A",
            "Cross-user profile leak")
    require(request("GET", "/saved", token=b)[1] == [], "New account saved looks not empty")
    status_a, profile_a = request("GET", "/profile", token=a)
    require(status_a == 200 and profile_a.get("notes") == "private smoke A", "Own profile not restored")
    require(profile_b.get("skin") is None, "New account has unexpected skin analysis")
    photo_id = upload_test_photo(a)
    require(photo_status(photo_id, a) == 200, "Owner cannot read its image")
    require(photo_status(photo_id, b) == 404, "Other account can read image")
    require(photo_status(photo_id, b, "DELETE") == 404, "Other account can delete image")
    require(photo_status(photo_id, a, "DELETE") == 200, "Owner deletion failed")
    require(photo_status(photo_id, a) == 404, "Deleted image remains readable")

    require(request("GET", "/profile")[0] == 401, "Missing authorization was accepted")
    require(request("POST", "/logout", token=a)[0] == 200, "Logout failed")
    require(request("GET", "/me", token=a)[0] == 401, "Revoked session still accepted")
    require(request("GET", "/me", token=b)[0] == 200, "Other session unexpectedly invalidated")
    require(request("POST", "/logout", token=b)[0] == 200, "Logout B failed")
    print("PASS: live registration, account-specific profiles, generated test-photo upload/isolation/deletion, logout and revocation")
    print("NOT tested: clock-based expiry, remote-provider storage deletion, browser cookie/device UI, provider AI")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
