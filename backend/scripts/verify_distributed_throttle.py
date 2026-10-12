"""Real-Mongo, private-only distributed login throttle verification.

Requires existing Codespaces Mongo running on loopback and a dedicated isolated
test database. Starts its own FastAPI on port 8013 with shared throttle enabled.
Does not send email or interact with customer accounts.
"""
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("LUMIERE_SHARED_THROTTLE_TEST_ACK") != "disposable-mongo":
    raise SystemExit("Refusing without disposable-mongo acknowledgement")
url = "http://127.0.0.1:8013"
env = {**os.environ,
       "MONGO_URL": "mongodb://127.0.0.1:27018",
       "DB_NAME": "lumiere_distributed_throttle_disposable",
       "LUMIERE_DISTRIBUTED_RATE_LIMIT": "1",
       "LUMIERE_PUBLIC_DEPLOYMENT": "0",
       "LUMIERE_PHOTO_STORAGE": "local",
       "LUMIERE_LOCAL_IMAGE_STORAGE": "1",
       "ENVIRONMENT": "development"}
log_path = ROOT.parent / ".lumiere-dev" / "shared-throttle-test.log"
log_path.parent.mkdir(parents=True, exist_ok=True)
log_file = log_path.open("w")
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8013"],
    cwd=ROOT, env=env, stdout=log_file, stderr=subprocess.STDOUT,
)
try:
    for _ in range(45):
        if process.poll() is not None:
            raise RuntimeError(f"Isolated backend stopped before ready (exit {process.returncode}). Inspect private log: {log_path}")
        try:
            urllib.request.urlopen(url + "/api/account/me", timeout=1)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                break
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError(f"Isolated backend not ready. Inspect private log: {log_path}")
    # A fresh, randomly chosen synthetic unknown user; no password is changed.
    import secrets
    email = "test-" + secrets.token_hex(12) + "@example.invalid"
    results = []
    for _ in range(6):
        body = json.dumps({"email": email, "password": "invalid test password 123"}).encode()
        req = urllib.request.Request(
            url + "/api/account/login", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                results.append(response.status)
        except urllib.error.HTTPError as error:
            results.append(error.code)
    assert results == [401] * 5 + [429], f"Unexpected login rate limit behavior: {results}"
    print("PASS: MongoDB shared login limiter returned 401 x5 then 429 on sixth attempt")
    print("No existing profiles, production secrets, photographs or mail used.")
finally:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    log_file.close()
