"""Mock-only SMTP recovery tests: no network, no secrets and no email delivery."""
import pytest
from services import account_recovery


def test_recovery_disabled_without_complete_configuration(monkeypatch):
    for key in ("LUMIERE_SMTP_HOST", "LUMIERE_SMTP_USER", "LUMIERE_SMTP_PASSWORD",
                "LUMIERE_RECOVERY_FROM", "LUMIERE_RECOVERY_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    assert not account_recovery.recovery_configured()
    with pytest.raises(RuntimeError, match="not configured"):
        account_recovery.send_recovery_email("recipient@example.invalid", "dummy")


def test_recovery_sends_only_one_private_https_link(monkeypatch):
    settings = {
        "LUMIERE_SMTP_HOST": "smtp.example.invalid",
        "LUMIERE_SMTP_USER": "test",
        "LUMIERE_SMTP_PASSWORD": "dummy-not-a-real-secret",
        "LUMIERE_SMTP_PORT": "587",
        "LUMIERE_RECOVERY_FROM": "sender@example.invalid",
        "LUMIERE_RECOVERY_BASE_URL": "https://example.invalid",
    }
    for k, v in settings.items():
        monkeypatch.setenv(k, v)
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.invalid", 587, 15)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self, context=None):
            assert context is not None
            sent.append("tls")
        def login(self, user, password):
            assert (user, password) == ("test", "dummy-not-a-real-secret")
            sent.append("auth")
        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr(account_recovery.smtplib, "SMTP", FakeSMTP)
    assert account_recovery.recovery_configured()
    account_recovery.send_recovery_email("recipient@example.invalid", "token+with /symbols")
    assert sent[:2] == ["tls", "auth"]
    msg = sent[2]
    assert msg["To"] == "recipient@example.invalid"
    assert msg["From"] == "sender@example.invalid"
    assert msg["Subject"] == "Reset your LUMIÈRE password"
    body = msg.get_content()
    assert "https://example.invalid/account?reset_token=token%2Bwith%20%2Fsymbols" in body
    assert "30 minutes" in body


def test_recovery_requires_https(monkeypatch):
    for k, v in {
        "LUMIERE_SMTP_HOST": "smtp.example.invalid",
        "LUMIERE_SMTP_USER": "test",
        "LUMIERE_SMTP_PASSWORD": "dummy",
        "LUMIERE_RECOVERY_FROM": "sender@example.invalid",
        "LUMIERE_RECOVERY_BASE_URL": "http://example.invalid",
    }.items():
        monkeypatch.setenv(k, v)
    assert not account_recovery.recovery_configured()
