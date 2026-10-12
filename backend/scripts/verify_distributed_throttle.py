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
urls = ["http://127.0.0.1:8013", "http://127.0.0.1:8014"]
env = {**os.environ,
       "MONGO_URL": "mongodb://127.0.0.1:27018",
       "DB_NAME": "lumiere_distributed_throttle_disposable",
       "LUMIERE_DISTRIBUTED_RATE_LIMIT": "1",
       "LUMIERE_PUBLIC_DEPLOYMENT": "0",
       "LUMIERE_PHOTO_STORAGE": "local",
       "LUMIERE_LOCAL_IMAGE_STORAGE": "1",
       "ENVIRONMENT": "development"}
log_dir = ROOT.parent / ".lumiere-dev"
log_dir.mkdir(parents=True, exist_ok=True)
processes = []
logs = []
try:
    for port in (8013, 8014):
        log_path = log_dir / f"shared-throttle-{port}.log"
        log_handle = log_path.open("w")
        logs.append(log_handle)
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT,
        )
        processes.append(process)
    for url, process in zip(urls, processes):
        for _ in range(45):
            if process.poll() is not None:
                raise RuntimeError(f"Test backend at {url} exited; inspect {log_dir}/shared-throttle-*.log")
            try:
                urllib.request.urlopen(url + "/api/account/me", timeout=1)
            except urllib.error.HTTPError as error:
                if error.code == 401:
                    break
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError(f"Backend at {url} not ready; inspect private test logs")
    import secrets
    email = "test-" + secrets.token_hex(12) + "@example.invalid"
    results = []
    for attempt in range(6):
        body = json.dumps({"email": email, "password": "invalid test password 123"}).encode()
        req = urllib.request.Request(
            urls[attempt % 2] + "/api/account/login", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                results.append(response.status)
        except urllib.error.HTTPError as error:
            results.append(error.code)
    assert results == [401] * 5 + [429], f"Unexpected cross-process result: {results}"
    print("PASS: two independent FastAPI processes shared MongoDB login limiter (401 x5 then 429)")
    print("No existing customer records, photographs, real passwords or mail were used.")
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for log in logs:
        log.close()
