"""Sentry stays off by default and never forwards sensitive request data."""
from app.core import monitoring
from app.core.config import settings


def test_off_without_a_dsn(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "")
    assert monitoring.init_monitoring() is False


def test_bad_dsn_never_breaks_startup(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "not-a-dsn")
    monkeypatch.setattr(monitoring, "_enabled", False)
    assert monitoring.init_monitoring() is False  # logged, not raised


def test_scrub_removes_bodies_cookies_auth_and_user():
    event = {
        "request": {
            "url": "https://api.test/api/v1/members", "method": "POST", "data": {"phone": "0244000000"},
            "cookies": {"s": "x"}, "query_string": "email=a@b.test",
            "headers": {"Authorization": "Bearer abc", "Cookie": "s=x", "User-Agent": "ua", "X-Request-ID": "r1"},
        },
        "user": {"email": "a@b.test", "ip_address": "1.2.3.4"},
        "exception": {"values": []},
    }
    out = monitoring._scrub(event, {})
    assert "data" not in out["request"] and "cookies" not in out["request"] and "query_string" not in out["request"]
    assert out["request"]["headers"] == {"User-Agent": "ua", "X-Request-ID": "r1"}
    assert "user" not in out and "exception" in out


def test_tag_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(monitoring, "_enabled", False)
    monitoring.tag(church_id="x", request_id="y")  # must not raise
