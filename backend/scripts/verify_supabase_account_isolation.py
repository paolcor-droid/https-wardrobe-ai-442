"""Run real account-isolation + private Supabase test-bucket integration locally.

Uses a dedicated disposable Mongo database and port 8012. Existing app at
8000/8081, real accounts and existing photos remain untouched.
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
if os.environ.get("LUMIERE_SUPABASE_ACCOUNT_E2E_ACK") != "test-bucket-disposable-database":
    raise SystemExit("Refusing without explicit disposable-database and test-bucket acknowledgement")
if not os.environ.get("LUMIERE_SUPABASE_URL", "").startswith("https://"):
    raise SystemExit("Supabase HTTPS URL required")
if not os.environ.get("LUMIERE_SUPABASE_SERVICE_ROLE_KEY"):
    raise SystemExit("Supabase service-role secret missing")
bucket = os.environ.get("LUMIERE_SUPABASE_BUCKET", "")
if bucket != os.environ.get("LUMIERE_SUPABASE_TEST_BUCKET") or "test" not in bucket.lower():
    raise SystemExit("Refusing to run against a non-test Supabase bucket")
if os.environ.get("LUMIERE_PUBLIC_DEPLOYMENT") == "1":
    raise SystemExit("Refusing production deployment")
# Confirm the bucket is private using Supabase's admin API before any uploads.
bucket_req = urllib.request.Request(
    os.environ["LUMIERE_SUPABASE_URL"].rstrip("/") + "/storage/v1/bucket/" + bucket,
    headers={
        "apikey": os.environ["LUMIERE_SUPABASE_SERVICE_ROLE_KEY"],
        "Authorization": "Bearer " + os.environ["LUMIERE_SUPABASE_SERVICE_ROLE_KEY"],
    },
)
with urllib.request.urlopen(bucket_req, timeout=15) as response:
    bucket_info = json.load(response)
if bucket_info.get("public") is not False:
    raise SystemExit("Refusing: Supabase test bucket is public or privacy cannot be confirmed")
print("PASS: Supabase test bucket confirmed PRIVATE")
env = dict(os.environ)
env.update({
    "MONGO_URL": "mongodb://127.0.0.1:27018",
    "DB_NAME": "lumiere_supabase_e2e_disposable",
    "LUMIERE_PHOTO_STORAGE": "supabase",
    "LUMIERE_LOCAL_IMAGE_STORAGE": "0",
    "LUMIERE_PUBLIC_DEPLOYMENT": "0",
    "ENVIRONMENT": "development",
})
base = "http://127.0.0.1:8012"
with subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8012"],
    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
) as process:
    try:
        ready = False
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Isolated test backend exited; check startup dependencies")
            try:
                urllib.request.urlopen(base + "/api/account/me", timeout=2)
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    ready = True
                    break
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(1)
        if not ready:
            raise RuntimeError("Isolated test backend never became ready")
        test_env = dict(env)
        test_env.update({
            "LUMIERE_LIVE_TEST_ACK": "disposable-database",
            "LUMIERE_LIVE_API_URL": base,
        })
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "live_account_smoke.py")],
            cwd=ROOT, env=test_env, check=False, timeout=180,
        )
        if result.returncode:
            raise RuntimeError("Supabase backed 2-account integration test failed")
        print("PASS: real Supabase storage through FastAPI, owner-only read/delete, account isolation and 404 readback")
        print("Existing Codespaces backend and accounts were not modified.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
