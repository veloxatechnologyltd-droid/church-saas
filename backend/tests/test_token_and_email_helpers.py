import logging

import pytest

from app.core import security
from app.services import email as email_service
from app.services.email import ConsoleEmailSender, EmailMessage, FakeEmailSender


def test_generated_tokens_are_unique_and_hash_consistently():
    raw_a, hash_a = security.generate_token()
    raw_b, hash_b = security.generate_token()
    assert raw_a != raw_b and hash_a != hash_b
    assert security.hash_token(raw_a) == hash_a
    assert raw_a not in hash_a and len(hash_a) == 64
    assert len(raw_a) >= 40  # 256 bits of entropy


def test_access_token_has_a_fractional_issue_time():
    claims = security.decode_token(security.create_access_token({"sub": "x"}))
    assert isinstance(claims["iat"], float) and claims["exp"] > claims["iat"]


def test_fake_sender_collects_messages():
    sender = FakeEmailSender()
    message = EmailMessage(to="a@b.co", subject="s", body="b")
    sender.send(message)
    assert sender.outbox == [message]


def test_console_sender_logs_instead_of_sending(caplog):
    with caplog.at_level(logging.WARNING, logger="app.email"):
        ConsoleEmailSender().send(EmailMessage(to="a@b.co", subject="Hello", body="the link"))
    assert "not delivered" in caplog.text and "the link" in caplog.text


def test_unsupported_email_backend_is_refused_not_silently_dropped(monkeypatch):
    monkeypatch.setattr(email_service.settings, "EMAIL_BACKEND", "smtp")
    email_service.get_email_sender.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="not supported"):
            email_service.get_email_sender()
    finally:
        email_service.get_email_sender.cache_clear()


def test_default_backend_is_console():
    email_service.get_email_sender.cache_clear()
    assert isinstance(email_service.get_email_sender(), ConsoleEmailSender)
