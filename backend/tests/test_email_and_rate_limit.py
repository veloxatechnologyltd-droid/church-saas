"""SendGrid email sender and the shared (database) rate limiter."""
import httpx
import pytest

from app.core import middleware
from app.core.config import settings
from app.services import email as email_service
from app.services.email import EmailDeliveryError, EmailMessage, SendGridEmailSender


@pytest.fixture()
def sendgrid(monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "SG.test")
    monkeypatch.setattr(settings, "FROM_EMAIL", "hello@asafo.test")
    monkeypatch.setattr(settings, "FROM_NAME", "Asafo")


def _capture(monkeypatch, status=202, body=""):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return httpx.Response(status, text=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(email_service.httpx, "post", fake_post)
    return calls


def test_sendgrid_request_shape(sendgrid, monkeypatch):
    calls = _capture(monkeypatch)
    SendGridEmailSender().send(EmailMessage(to="a@b.test", subject="Hi", body="Link: https://x/y"))
    call = calls[0]
    assert call["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert call["headers"]["Authorization"] == "Bearer SG.test"
    assert call["json"]["personalizations"] == [{"to": [{"email": "a@b.test"}]}]
    assert call["json"]["from"] == {"email": "hello@asafo.test", "name": "Asafo"}
    assert call["json"]["content"] == [{"type": "text/plain", "value": "Link: https://x/y"}]


def test_sendgrid_error_raises_without_leaking_the_body(sendgrid, monkeypatch):
    _capture(monkeypatch, status=401, body='{"errors":[{"message":"bad key"}]}')
    with pytest.raises(EmailDeliveryError) as exc:
        SendGridEmailSender().send(EmailMessage(to="a@b.test", subject="Hi", body="secret-token-123"))
    assert "401" in str(exc.value) and "secret-token-123" not in str(exc.value)


def test_sendgrid_network_failure_is_wrapped(sendgrid, monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectTimeout("slow")

    monkeypatch.setattr(email_service.httpx, "post", boom)
    with pytest.raises(EmailDeliveryError):
        SendGridEmailSender().send(EmailMessage(to="a@b.test", subject="Hi", body="x"))


def test_sendgrid_needs_a_key(monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "")
    with pytest.raises(RuntimeError):
        SendGridEmailSender()


def test_backend_selection(monkeypatch, sendgrid):
    email_service.get_email_sender.cache_clear()
    try:
        monkeypatch.setattr(settings, "EMAIL_BACKEND", "sendgrid")
        assert isinstance(email_service.get_email_sender(), SendGridEmailSender)
        email_service.get_email_sender.cache_clear()
        monkeypatch.setattr(settings, "EMAIL_BACKEND", "smtp")
        with pytest.raises(RuntimeError):
            email_service.get_email_sender()
    finally:
        email_service.get_email_sender.cache_clear()


def test_a_failed_send_does_not_break_forgot_password(client, monkeypatch, sendgrid):
    """The reply must be identical whether or not delivery works."""
    from app.main import app

    class Broken:
        def send(self, message):
            raise EmailDeliveryError("down")

    app.dependency_overrides[email_service.get_email_sender] = lambda: Broken()
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200


class TestDatabaseRateLimiter:
    def test_limit_is_shared_between_instances(self, client):
        """Two limiter objects (= two serverless instances) must see the same counter."""
        a, b = middleware.DatabaseRateLimiter(), middleware.DatabaseRateLimiter()
        key = "1.2.3.4|POST|/x"
        assert a.hit(key, 2, 60) is None
        assert b.hit(key, 2, 60) is None
        wait = a.hit(key, 2, 60)  # third hit, over the limit of 2
        assert wait is not None and 1 <= wait <= 60

    def test_keys_are_independent(self, client):
        limiter = middleware.DatabaseRateLimiter()
        assert limiter.hit("a", 1, 60) is None
        assert limiter.hit("b", 1, 60) is None
        assert limiter.hit("a", 1, 60) is not None

    def test_login_is_throttled_through_the_app(self, client):
        for _ in range(10):
            assert client.post("/api/v1/auth/login", json={"email": "x@y.test", "password": "nope-nope"}).status_code != 429
        r = client.post("/api/v1/auth/login", json={"email": "x@y.test", "password": "nope-nope"})
        assert r.status_code == 429 and "Retry-After" in r.headers

    def test_fails_open_when_the_database_errors(self, client, monkeypatch):
        import app.db.database as database

        class BadEngine:
            def begin(self):
                raise RuntimeError("db down")

        monkeypatch.setattr(database, "engine", BadEngine())
        assert middleware.DatabaseRateLimiter().hit("k", 1, 60) is None

    def test_memory_backend_still_works(self, client, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_BACKEND", "memory")
        assert middleware.limiter.hit("m", 1, 60) is None
        assert middleware.limiter.hit("m", 1, 60) is not None
