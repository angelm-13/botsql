from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def _enabled(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "si", "sí", "on"}


def email_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") or os.getenv("MAIL_SERVER"))


def send_email(to_email: str, subject: str, text: str) -> bool:
    host = os.getenv("SMTP_HOST") or os.getenv("MAIL_SERVER") or ""
    if not email_configured():
        return False
    port = int(os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or "587")
    username = os.getenv("SMTP_USERNAME") or os.getenv("MAIL_USERNAME") or ""
    password = os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_PASSWORD") or ""
    sender = os.getenv("SMTP_FROM") or username or "noreply@localhost"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(text)
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if _enabled(os.getenv("SMTP_TLS", "true")):
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
    return True