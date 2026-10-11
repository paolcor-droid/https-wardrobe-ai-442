"""Opt-in smoke test against a RUNNING backend and disposable MongoDB.

Usage (in a private test environment ONLY):
 LUMIERE_LIVE_TEST_ACK=disposable-database LUMIERE_LIVE_API_URL=http://127.0.0.1:8000 \\
     python backend/scripts/live_account_smoke.py

This creates two real accounts (therefore requires a disposable test database). No
provider credentials or login tokens are printed. Does not alter production settings.
"""
import json
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
    require(request("GET", "/profile", token=b)[1].get("notes") != "private smoke A",
            "Cross-user profile leak")
    require(request("GET", "/saved", token=b)[1] == [], "New account saved looks not empty")
    require(request("GET", "/profile")[0] == 401, "Missing authorization was accepted")
    require(request("POST", "/logout", token=a)[0] == 200, "Logout failed")
    require(request("GET", "/me", token=a)[0] == 401, "Revoked session still accepted")
    require(request("GET", "/me", token=b)[0] == 200, "Other session unexpectedly invalidated")
    require(request("POST", "/logout", token=b)[0] == 200, "Logout B failed")
    print("PASS: live registration, login, privacy isolation, logout and revocation")
    print("NOT tested: clock-based expiry, remote storage deletion, device UI, provider AI")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
