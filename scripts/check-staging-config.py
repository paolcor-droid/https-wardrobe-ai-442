#!/usr/bin/env python3
"""Read-only LUMIÈRE staging configuration preflight. Never prints secret values.

Reads environment variables but does not make network calls or create resources.
Only run this against a staging/production environment, not the Codespaces preview.
"""
import os
import sys
from urllib.parse import urlsplit


def check(env=None):
    env = os.environ if env is None else env
    failures = []
    def require(condition, problem):
        if not condition:
            failures.append(problem)

    db_url = env.get("MONGO_URL", "")
    parts = urlsplit(db_url)
    require(parts.scheme in {"mongodb", "mongodb+srv"}, "MONGO_URL must be a MongoDB URL")
    require(bool(parts.hostname) and parts.hostname not in {"localhost", "127.0.0.1", "::1"},
            "Use a persistent external database, not localhost")
    require(env.get("DB_NAME", "").strip() != "", "DB_NAME is required")
    if parts.scheme == "mongodb":
        query = (parts.query or "").lower()
        require("tls=true" in query or "ssl=true" in query, "MongoDB staging requires TLS")
    require(env.get("LUMIERE_PHOTO_STORAGE") in {"s3", "supabase"},
            "Use configured private durable photo storage (s3 or supabase)")
    require(env.get("LUMIERE_LOCAL_IMAGE_STORAGE") == "0",
            "Disable local image storage in staging")
    origins = [x.strip() for x in env.get("LUMIERE_CORS_ORIGINS", "").split(",") if x.strip()]
    require(bool(origins), "Set explicit HTTPS CORS origins")
    require(all(x.startswith("https://") and "*" not in x and
                urlsplit(x).hostname and not urlsplit(x).username for x in origins),
            "All CORS origins must be explicit HTTPS origins")
    require(bool(env.get("OPENAI_API_KEY", "").strip()), "Configure the server-side OpenAI API key")
    return failures


if __name__ == "__main__":
    issues = check()
    if issues:
        print("STAGING CONFIGURATION NOT READY")
        for issue in issues:
            print("- " + issue)
        sys.exit(1)
    print("Basic staging configuration checks passed. Live security and storage verification still required.")
