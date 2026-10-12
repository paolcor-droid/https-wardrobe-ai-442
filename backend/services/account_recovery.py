"""SMTP delivery for single-use LUMIÈRE account recovery links.

Disabled when required environment configuration is absent. Never log tokens.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

def recovery_configured() -> bool:
    return all(os.environ.get(name) for name in (
        "LUMIERE_SMTP_HOST", "LUMIERE_SMTP_USER", "LUMIERE_SMTP_PASSWORD",
        "LUMIERE_RECOVERY_FROM", "LUMIERE_RECOVERY_BASE_URL",
    )) and os.environ["LUMIERE_RECOVERY_BASE_URL"].startswith("https://")

def send_recovery_email(email: str, token: str) -> None:
    if not recovery_configured():
        raise RuntimeError("Account recovery email is not configured")
    base = os.environ["LUMIERE_RECOVERY_BASE_URL"].rstrip("/")
    link = base + "/account?reset_token=" + quote(token, safe="")
    message = EmailMessage()
    message["Subject"] = "Reset your LUMIÈRE password"
    message["From"] = os.environ["LUMIERE_RECOVERY_FROM"]
    message["To"] = email
    message.set_content(
        "Use this single-use link within 30 minutes to reset your LUMIÈRE password:\n"
        + link + "\n\nIf you did not request this, ignore the message."
    )
    with smtplib.SMTP(os.environ["LUMIERE_SMTP_HOST"], int(os.environ.get("LUMIERE_SMTP_PORT", "587")), timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ["LUMIERE_SMTP_USER"], os.environ["LUMIERE_SMTP_PASSWORD"])
        smtp.send_message(message)
