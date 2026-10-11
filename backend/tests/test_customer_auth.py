from datetime import datetime, timezone
import pytest

from services.customer_auth import create_session, hash_password, normalize_email, token_digest, verify_password


def test_email_normalization_and_validation():
    assert normalize_email(" Person@Example.COM ") == "person@example.com"
    for value in ("missing-at", "a @example.com", "x" * 255):
        with pytest.raises(ValueError):
            normalize_email(value)


def test_password_hash_salted_and_verified():
    password = "Unique secure passphrase 2026"
    first, second = hash_password(password), hash_password(password)
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("wrong password", first)
    assert not verify_password(password, "not-a-hash")
    with pytest.raises(ValueError):
        hash_password("short")


def test_random_session_digest_and_expiry():
    token, digest, expiry = create_session()
    other, _, _ = create_session()
    assert token != other
    assert token_digest(token) == digest
    assert token != digest
    assert len(digest) == 64
    assert expiry > datetime.now(timezone.utc)
