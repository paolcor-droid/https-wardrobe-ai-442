"""Read-only LUMIÈRE release preflight: configuration without leaking secrets.

Does not send recovery mail, read customer data or activate public access.
Usage: PYTHONPATH=backend python backend/scripts/release_preflight.py
"""
import os
import sys
from urllib.parse import urlsplit

from services.account_recovery import recovery_configured

results = []

def check(name, ok, note=""):
    results.append((name, bool(ok), note))
    print(("PASS" if ok else "BLOCKED") + ": " + name + ((" — " + note) if note else ""))

check("SMTP password recovery configured", recovery_configured(),
      "configuration only; real email delivery must be tested")
recovery_url = os.getenv("LUMIERE_RECOVERY_BASE_URL", "")
p = urlsplit(recovery_url)
check("HTTPS recovery origin", p.scheme == "https" and bool(p.hostname) and
      not p.username and not p.password and not p.query and not p.fragment,
      "recovery origin must be HTTPS")
check("Distributed rate limiter", os.getenv("LUMIERE_DISTRIBUTED_RATE_LIMIT_VERIFIED") == "1",
      "existing process-local throttle is not production-grade")
check("Real iOS/Android sign-off", os.getenv("LUMIERE_REAL_DEVICE_SIGNOFF") == "1",
      "Expo Metro bundle exports are not physical-device testing")
check("Storage-provider backup retention signed off", os.getenv("LUMIERE_STORAGE_RETENTION_SIGNOFF") == "1",
      "object DELETE+404 is not evidence of replica/backup purge")
check("Public deployment remains gated", os.getenv("LUMIERE_PUBLIC_DEPLOYMENT", "0") != "1",
      "do not activate public access during preflight")
print(f"Summary: {sum(ok for _, ok, _ in results)}/{len(results)} checks passed")
if not all(ok for _, ok, _ in results):
    print("RELEASE BLOCKED: do not interpret this preflight as an authorization to launch.")
    sys.exit(2)
print("Preflight config flags satisfied; evidence and manual security approval are still required.")
