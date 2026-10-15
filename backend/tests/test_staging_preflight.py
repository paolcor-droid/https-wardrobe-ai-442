"""No-network staging configuration preflight regression tests."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "staging_config_check",
    Path(__file__).resolve().parents[2] / "scripts" / "check-staging-config.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def valid():
    return {
        "MONGO_URL": "mongodb+srv://user:placeholder@cluster.example.invalid/db",
        "DB_NAME": "lumiere_staging",
        "LUMIERE_PHOTO_STORAGE": "s3",
        "LUMIERE_LOCAL_IMAGE_STORAGE": "0",
        "LUMIERE_CORS_ORIGINS": "https://staging.example.invalid",
        "OPENAI_API_KEY": "placeholder-never-used",
    }


def test_ready_config_passes():
    assert module.check(valid()) == []


def test_local_database_and_storage_are_blocked():
    env = valid()
    env["MONGO_URL"] = "mongodb://127.0.0.1:27017"
    env["LUMIERE_PHOTO_STORAGE"] = "local"
    env["LUMIERE_LOCAL_IMAGE_STORAGE"] = "1"
    assert len(module.check(env)) >= 3


def test_insecure_origins_and_missing_key_are_blocked():
    env = valid()
    env["LUMIERE_CORS_ORIGINS"] = "http://test.example.invalid,*"
    env["OPENAI_API_KEY"] = ""
    assert len(module.check(env)) >= 2


def test_plain_mongodb_requires_tls():
    env = valid()
    env["MONGO_URL"] = "mongodb://cluster.example.invalid/staging"
    assert any("TLS" in x for x in module.check(env))
    env["MONGO_URL"] += "?tls=true"
    assert module.check(env) == []
