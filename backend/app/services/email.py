"""Outgoing email behind a small interface.

Only a console sender (development) and a fake sender (tests) exist. There is no real
provider yet: wiring one up (SendGrid is already a dependency) is blocked on a new dev
key, and ``EMAIL_BACKEND`` other than ``console`` is rejected rather than silently
dropping mail.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("app.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    """Development only: writes the email, including any secret link, to the server log."""

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "EMAIL (console backend, not delivered)\nTo: %s\nSubject: %s\n\n%s",
            message.to, message.subject, message.body,
        )


class FakeEmailSender:
    """Tests: collects messages instead of sending them."""

    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)


@lru_cache
def get_email_sender() -> EmailSender:
    """FastAPI dependency; override it in tests."""
    if settings.EMAIL_BACKEND == "console":
        return ConsoleEmailSender()
    raise RuntimeError(
        f"EMAIL_BACKEND={settings.EMAIL_BACKEND!r} is not supported yet. Only 'console' exists; "
        "a real provider needs a new dev key first."
    )


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
