"""Staged authentication primitives; do not authorize legacy routes with these tokens."""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

ITERATIONS = 600_000


def normalize_email(email: str) -> str:
    value = email.strip().casefold()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Invalid email address")
    return value


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 1024:
        raise ValueError("Password must be 12 to 1024 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (ITERATIONS, salt.hex(), digest.hex())


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
        rounds = int(rounds)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= rounds <= 1_000_000:
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(hours: int = 24) -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(32)
    return token, token_digest(token), datetime.now(timezone.utc) + timedelta(hours=hours)
