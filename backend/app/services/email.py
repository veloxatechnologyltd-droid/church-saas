"""Outgoing email behind a small interface.

* ``SendGridEmailSender`` (``EMAIL_BACKEND=sendgrid``): production. Calls the SendGrid v3 HTTP
  API directly with ``httpx``; needs ``SENDGRID_API_KEY`` and a verified ``FROM_EMAIL``.
* ``ConsoleEmailSender`` (``EMAIL_BACKEND=console``): development only, logs the message.
* ``FakeEmailSender``: tests.

An unknown ``EMAIL_BACKEND`` is rejected rather than silently dropping mail. Callers treat a
failed send as non-fatal (the invitation or reset token already exists), so ``send`` raises
``EmailDeliveryError`` and never includes the message body (it holds secret links) in errors.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger("app.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailDeliveryError(RuntimeError):
    """The email provider refused or could not be reached."""


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    """Development only: writes the email, including any secret link, to the server log."""

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "EMAIL (console backend, not delivered)\nTo: %s\nSubject: %s\n\n%s",
            message.to, message.subject, message.body,
        )


class SendGridEmailSender:
    """Production: SendGrid v3 ``mail/send`` (plain text; links are the only content that matters)."""

    URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self) -> None:
        if not settings.SENDGRID_API_KEY:
            raise RuntimeError("SENDGRID_API_KEY is not configured")

    def send(self, message: EmailMessage) -> None:
        payload = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {"email": settings.FROM_EMAIL, "name": settings.FROM_NAME},
            "subject": message.subject,
            "content": [{"type": "text/plain", "value": message.body}],
        }
        try:
            response = httpx.post(
                self.URL,
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                json=payload,
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise EmailDeliveryError(f"SendGrid request failed: {type(exc).__name__}") from exc
        if response.status_code != 202:  # SendGrid answers 202 Accepted on success
            raise EmailDeliveryError(f"SendGrid rejected the email (HTTP {response.status_code}): {response.text[:300]}")


class FakeEmailSender:
    """Tests: collects messages instead of sending them."""

    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)


@lru_cache
def get_email_sender() -> EmailSender:
    """FastAPI dependency; override it in tests."""
    backend = settings.EMAIL_BACKEND.strip().lower()
    if backend == "console":
        return ConsoleEmailSender()
    if backend == "sendgrid":
        return SendGridEmailSender()
    raise RuntimeError(f"EMAIL_BACKEND={settings.EMAIL_BACKEND!r} is not supported (use 'sendgrid' or 'console')")


def invitation_email(*, to: str, church_name: str, role: str, link: str, expires_hours: int) -> EmailMessage:
    role_label = role.replace("_", " ")
    return EmailMessage(
        to=to,
        subject=f"You are invited to join {church_name}",
        body=(
            f"You have been invited to join {church_name} as {role_label}.\n\n"
            f"Accept the invitation: {link}\n\n"
            f"This link works once and expires in {expires_hours} hours. "
            "If you did not expect this, you can ignore this email."
        ),
    )


def password_reset_email(*, to: str, link: str, expires_minutes: int) -> EmailMessage:
    return EmailMessage(
        to=to,
        subject="Reset your password",
        body=(
            f"Use this link to choose a new password: {link}\n\n"
            f"It works once and expires in {expires_minutes} minutes. "
            "If you did not ask for this, you can ignore this email; your password is unchanged."
        ),
    )
