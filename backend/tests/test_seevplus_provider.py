"""Seevplus billing provider: checkout request shape, signed webhooks, amount safety."""
import hashlib
import hmac
import json
import time

import httpx
import pytest

from app.core.config import settings
from app.models import Invoice
from app.services import billing
from tests.test_auth_api import bearer

SIGNUP = {
    "church_name": "Grace Chapel Accra", "first_name": "Akosua", "last_name": "Owusu",
    "email": "akosua@grace.test", "password": "very-secret-1", "phone": "0244000000", "accept_terms": True,
}
SECRET = "whsec_test"


@pytest.fixture(autouse=True)
def _seevplus(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "console")
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "seevplus")
    monkeypatch.setattr(settings, "SEEVPLUS_API_KEY", "sk_test_123")
    monkeypatch.setattr(settings, "BILLING_WEBHOOK_SECRET", SECRET)


@pytest.fixture()
def seev_api(monkeypatch):
    """Capture the outgoing checkout request and answer like Seevplus does."""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return httpx.Response(201, json={"success": True, "data": {
            "reference": f"PAY-TEST-{len(calls)}", "status": "pending",
            "checkout_url": f"https://pay.seevplus.test/c/{len(calls)}",
        }}, request=httpx.Request("POST", url))

    monkeypatch.setattr(billing.httpx, "post", fake_post)
    return calls


@pytest.fixture()
def owner(client):
    r = client.post("/api/v1/signup", json=SIGNUP)
    assert r.status_code == 201, r.text
    return bearer(r.json()["data"]["access_token"])


def _buy(client, owner):
    r = client.post("/api/v1/sms-credits/purchase", json={"pack_code": "sms_2000"}, headers=owner)
    assert r.status_code == 200, r.text
    return r.json()["data"]["invoice"]


def _signed(body: dict, *, ts=None, secret=SECRET):
    raw = json.dumps(body).encode()
    ts = str(int(time.time()) if ts is None else ts)
    sig = "v1=" + hmac.new(secret.encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return raw, {"X-Seev-Timestamp": ts, "X-Seev-Signature": sig, "X-Seev-Event-ID": "evt_x"}


def _event(ref, amount, status="completed", event="payment.succeeded", currency="GHS", eid="evt_1"):
    return {"id": eid, "event": event, "env": "sandbox", "createdAt": "2026-11-10T10:00:00Z",
            "data": {"transaction": {"reference": ref, "status": status, "amount": amount, "currency": currency}}}


def test_checkout_request_shape(client, session, owner, seev_api):
    invoice = _buy(client, owner)
    call = seev_api[0]
    assert call["url"] == "https://api.seevplus.com/api/v1/developer/payments"
    assert call["headers"]["Authorization"] == "Bearer sk_test_123"
    assert call["headers"]["Idempotency-Key"] == f"invoice_{invoice['id']}"
    body = call["json"]
    assert body["type"] == "checkout" and body["currency"] == "GHS" and body["channels"] == ["mobile_money"]
    assert body["amount"] == int(invoice["amount"] * 100)  # pesewas, not cedis
    assert body["recipient"]["email"] == "akosua@grace.test"
    assert body["meta"]["invoiceId"] == invoice["id"]
    assert invoice["checkout_url"].startswith("https://pay.seevplus.test/")
    assert session.get(Invoice, invoice["id"]).provider_ref == "PAY-TEST-1"


def test_provider_failure_is_502_and_leaves_no_invoice(client, session, owner, monkeypatch):
    monkeypatch.setattr(billing.httpx, "post", lambda *a, **k: httpx.Response(
        502, json={"error": "bad_gateway", "message": "upstream"}, request=httpx.Request("POST", "http://x")))
    r = client.post("/api/v1/sms-credits/purchase", json={"pack_code": "sms_2000"}, headers=owner)
    assert r.status_code == 502
    assert client.get("/api/v1/billing/invoices", headers=owner).json()["total"] == 0


def test_signed_webhook_pays_invoice_once(client, session, owner, seev_api):
    invoice = _buy(client, owner)
    ref = session.get(Invoice, invoice["id"]).provider_ref
    raw, headers = _signed(_event(ref, invoice["amount"]))
    ok = client.post("/api/v1/billing/webhooks/seevplus", content=raw, headers=headers)
    assert ok.status_code == 200 and ok.json()["data"]["duplicate"] is False
    # A manual replay has a new envelope id but the same reference + status: still applied once.
    raw2, headers2 = _signed(_event(ref, invoice["amount"], eid="evt_replay"))
    dup = client.post("/api/v1/billing/webhooks/seevplus", content=raw2, headers=headers2)
    assert dup.json()["data"]["duplicate"] is True
    balance = client.get("/api/v1/sms-credits", headers=owner).json()["data"]["balance"]
    assert balance == settings.SIGNUP_SMS_CREDITS + 2000


@pytest.mark.parametrize("mutate", ["bad_sig", "stale", "wrong_secret"])
def test_bad_webhooks_are_rejected(client, session, owner, seev_api, mutate):
    invoice = _buy(client, owner)
    ref = session.get(Invoice, invoice["id"]).provider_ref
    body = _event(ref, invoice["amount"])
    if mutate == "bad_sig":
        raw, headers = _signed(body)
        headers["X-Seev-Signature"] = "v1=" + "0" * 64
    elif mutate == "stale":
        raw, headers = _signed(body, ts=int(time.time()) - 3600)
    else:
        raw, headers = _signed(body, secret="someone-else")
    r = client.post("/api/v1/billing/webhooks/seevplus", content=raw, headers=headers)
    assert r.status_code == 400
    assert client.get("/api/v1/sms-credits", headers=owner).json()["data"]["balance"] == settings.SIGNUP_SMS_CREDITS


def test_amount_mismatch_does_not_grant(client, session, owner, seev_api):
    invoice = _buy(client, owner)
    ref = session.get(Invoice, invoice["id"]).provider_ref
    raw, headers = _signed(_event(ref, 1))  # paid GHS 1 for a bigger invoice
    assert client.post("/api/v1/billing/webhooks/seevplus", content=raw, headers=headers).status_code == 200
    assert client.get("/api/v1/sms-credits", headers=owner).json()["data"]["balance"] == settings.SIGNUP_SMS_CREDITS
    assert session.get(Invoice, invoice["id"]).status == "open"


def test_failed_payment_marks_invoice_failed(client, session, owner, seev_api):
    invoice = _buy(client, owner)
    ref = session.get(Invoice, invoice["id"]).provider_ref
    raw, headers = _signed(_event(ref, invoice["amount"], status="failed", event="payment.failed"))
    client.post("/api/v1/billing/webhooks/seevplus", content=raw, headers=headers)
    assert session.get(Invoice, invoice["id"]).status == "failed"


def test_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "SEEVPLUS_API_KEY", "")
    with pytest.raises(RuntimeError):
        billing.get_provider()
