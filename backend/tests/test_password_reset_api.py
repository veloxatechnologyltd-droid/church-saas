"""Forgot / reset password, and the guarantees around the emailed token."""
import re
from datetime import datetime, timedelta, timezone

import pytest

from app.models import PasswordResetToken
from tests.helpers import DEFAULT_PASSWORD, make_church, make_membership, make_user
from tests.test_auth_api import ANY_ROLE, bearer, login

NEW_PASSWORD = "a-much-better-password"


def forgot(client, email):
    return client.post("/api/v1/auth/forgot-password", json={"email": email})


def reset(client, token, password=NEW_PASSWORD):
    return client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": password})


def token_from(outbox, index=-1):
    match = re.search(r"token=([\w-]+)", outbox.outbox[index].body)
    assert match, outbox.outbox[index].body
    return match.group(1)


@pytest.fixture()
def user(session):
    u = make_user(session, "ama@example.com")
    make_membership(session, make_church(session), u, "secretary")
    return u


class TestForgot:
    def test_existing_user_gets_an_email_with_a_link(self, client, outbox, user):
        response = forgot(client, "ama@example.com")
        assert response.status_code == 200
        assert len(outbox.outbox) == 1 and outbox.outbox[0].to == "ama@example.com"
        assert "/reset-password?token=" in outbox.outbox[0].body

    def test_only_a_hash_is_stored(self, client, session, outbox, user):
        forgot(client, "ama@example.com")
        raw = token_from(outbox)
        row = session.query(PasswordResetToken).one()
        assert row.token_hash != raw and raw not in row.token_hash

    def test_unknown_email_gets_the_identical_reply_and_no_email(self, client, outbox, user):
        known, unknown = forgot(client, "ama@example.com"), forgot(client, "ghost@example.com")
        assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
        assert len(outbox.outbox) == 1  # only the real account was mailed

    def test_inactive_user_gets_the_same_reply_and_no_email(self, client, session, outbox):
        make_user(session, "off@example.com", is_active=False)
        assert forgot(client, "off@example.com").status_code == 200
        assert outbox.outbox == []

    def test_email_is_case_insensitive(self, client, outbox, user):
        forgot(client, " AMA@Example.com ")
        assert len(outbox.outbox) == 1

    def test_a_delivery_failure_does_not_change_the_reply(self, client, outbox, user):
        outbox.send = lambda message: (_ for _ in ()).throw(RuntimeError("smtp down"))
        assert forgot(client, "ama@example.com").status_code == 200

    def test_a_new_request_voids_the_previous_link(self, client, outbox, user):
        forgot(client, "ama@example.com")
        first = token_from(outbox)
        forgot(client, "ama@example.com")
        second = token_from(outbox)
        assert reset(client, first).status_code == 400
        assert reset(client, second).status_code == 200


class TestReset:
    def test_sets_the_new_password(self, client, outbox, user):
        forgot(client, "ama@example.com")
        assert reset(client, token_from(outbox)).status_code == 200
        assert login(client, "ama@example.com", NEW_PASSWORD).status_code == 200
        assert login(client, "ama@example.com", DEFAULT_PASSWORD).status_code == 401

    def test_single_use(self, client, outbox, user):
        forgot(client, "ama@example.com")
        raw = token_from(outbox)
        assert reset(client, raw).status_code == 200
        assert reset(client, raw, "yet-another-password").status_code == 400
        assert login(client, "ama@example.com", NEW_PASSWORD).status_code == 200  # second attempt changed nothing

    def test_expired(self, client, session, outbox, user):
        forgot(client, "ama@example.com")
        session.query(PasswordResetToken).update({PasswordResetToken.expires_at: datetime.now(timezone.utc) - timedelta(seconds=1)})
        session.flush()
        response = reset(client, token_from(outbox))
        assert response.status_code == 400 and "invalid or has expired" in response.json()["detail"]
        assert login(client, "ama@example.com", DEFAULT_PASSWORD).status_code == 200

    def test_default_lifetime_is_an_hour(self, client, session, outbox, user):
        forgot(client, "ama@example.com")
        row = session.query(PasswordResetToken).one()
        minutes = (row.expires_at - datetime.now(timezone.utc)).total_seconds() / 60
        assert 59 < minutes <= 60

    @pytest.mark.parametrize("token", ["", "garbage", "x" * 300])
    def test_unknown_token(self, client, token):
        assert reset(client, token).status_code in (400, 422)

    @pytest.mark.parametrize("password", ["short", "x" * 73])
    def test_password_length_limits_do_not_burn_the_token(self, client, outbox, user, password):
        forgot(client, "ama@example.com")
        raw = token_from(outbox)
        assert reset(client, raw, password).status_code == 422
        assert reset(client, raw).status_code == 200

    def test_ends_every_existing_session(self, client, outbox, user):
        old_session = login(client, "ama@example.com").json()["data"]["access_token"]
        assert client.get(ANY_ROLE, headers=bearer(old_session)).status_code == 200
        forgot(client, "ama@example.com")
        reset(client, token_from(outbox))
        assert client.get(ANY_ROLE, headers=bearer(old_session)).status_code == 401
        new_session = login(client, "ama@example.com", NEW_PASSWORD).json()["data"]["access_token"]
        assert client.get(ANY_ROLE, headers=bearer(new_session)).status_code == 200

    def test_cannot_reset_a_user_deactivated_after_requesting(self, client, outbox, user):
        forgot(client, "ama@example.com")
        user.is_active = False
        assert reset(client, token_from(outbox)).status_code == 400

    def test_reset_does_not_sign_anyone_in(self, client, outbox, user):
        forgot(client, "ama@example.com")
        assert "access_token" not in reset(client, token_from(outbox)).text
