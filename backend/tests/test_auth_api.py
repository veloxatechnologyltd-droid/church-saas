"""Auth through the real FastAPI app on a real database: login, tokens, church switching, roles."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.dependencies import CurrentUser, require_platform_admin
from app.db.database import engine, get_db
from tests.helpers import (
    DEFAULT_PASSWORD, make_branch, make_church, make_member, make_membership, make_user,
)

# Any-role tenant endpoint, and an admin-only one. Both only read.
ANY_ROLE = "/api/v1/members/"
ADMIN_ONLY = "/api/v1/audit/"


def login(client, email, password=DEFAULT_PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def claims_of(token):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def forge(claims, secret=None, **overrides):
    """Sign arbitrary claims, as an attacker with (or without) the key would."""
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5), **claims, **overrides}
    return jwt.encode(payload, secret or settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def test_app_engine_points_at_the_test_database():
    """If this fails, tests could be reading or writing the dev database."""
    assert make_url(str(engine.url)).database.endswith("_test")


# -------------------------------------------------------------------- login

class TestLogin:
    def test_single_church_signs_straight_in(self, client, session):
        church = make_church(session)
        user = make_user(session, "ama@example.com")
        make_membership(session, church, user, "secretary")

        response = login(client, "ama@example.com")

        assert response.status_code == 200
        data = response.json()["data"]
        claims = claims_of(data["access_token"])
        assert claims["sub"] == str(user.id)
        assert claims["church_id"] == str(church.id)
        assert claims["role"] == "secretary"
        assert "branch_id" not in claims
        assert data["active_church"]["id"] == str(church.id)
        assert [c["id"] for c in data["churches"]] == [str(church.id)]
        assert data["user"]["role"] == "secretary"
        assert data["user"]["church_id"] == str(church.id)
        assert client.get(ANY_ROLE, headers=bearer(data["access_token"])).status_code == 200

    def test_branch_scoped_membership_puts_branch_in_the_token(self, client, session):
        church = make_church(session)
        branch = make_branch(session, church)
        user = make_user(session, "kofi@example.com")
        make_membership(session, church, user, "secretary", branch_id=branch.id)

        data = login(client, "kofi@example.com").json()["data"]

        assert claims_of(data["access_token"])["branch_id"] == str(branch.id)
        assert data["active_church"]["branch_id"] == str(branch.id)

    def test_member_id_of_the_active_church_is_reported(self, client, session):
        church = make_church(session)
        member = make_member(session, church)
        user = make_user(session, "yaa@example.com")
        make_membership(session, church, user, "member", member_id=member.id)

        assert login(client, "yaa@example.com").json()["data"]["user"]["member_id"] == str(member.id)

    def test_several_churches_get_a_church_less_token_and_must_choose(self, client, session):
        a, b = make_church(session, "alpha-church"), make_church(session, "beta-church")
        user = make_user(session, "multi@example.com")
        make_membership(session, a, user, "church_admin")
        make_membership(session, b, user, "finance")

        data = login(client, "multi@example.com").json()["data"]

        assert "church_id" not in claims_of(data["access_token"])
        assert data["active_church"] is None
        assert [c["slug"] for c in data["churches"]] == ["alpha-church", "beta-church"]
        response = client.get(ANY_ROLE, headers=bearer(data["access_token"]))
        assert response.status_code == 403
        assert "No church selected" in response.json()["detail"]

    def test_email_is_case_insensitive(self, client, session):
        make_membership(session, make_church(session), make_user(session, "case@example.com"))
        assert login(client, "  CASE@Example.com ").status_code == 200

    @pytest.mark.parametrize("email,password", [("nobody@example.com", DEFAULT_PASSWORD), ("real@example.com", "wrong-password")])
    def test_bad_credentials_get_the_same_401(self, client, session, email, password):
        make_membership(session, make_church(session), make_user(session, "real@example.com"))
        response = login(client, email, password)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_inactive_user_cannot_log_in(self, client, session):
        make_membership(session, make_church(session), make_user(session, "off@example.com", is_active=False))
        assert login(client, "off@example.com").status_code == 401

    def test_user_with_no_church_is_refused(self, client, session):
        make_user(session, "lonely@example.com")
        response = login(client, "lonely@example.com")
        assert response.status_code == 403
        assert "not a member of any church" in response.json()["detail"]

    def test_inactive_membership_does_not_count(self, client, session):
        make_membership(session, make_church(session), make_user(session, "gone@example.com"), is_active=False)
        assert login(client, "gone@example.com").status_code == 403

    def test_closed_church_does_not_count(self, client, session):
        church = make_church(session)
        church.status = "closed"
        make_membership(session, church, make_user(session, "closed@example.com"))
        session.flush()
        assert login(client, "closed@example.com").status_code == 403

    def test_platform_admin_without_a_church_can_log_in_but_not_use_church_endpoints(self, client, session):
        make_user(session, "owner@example.com", is_platform_admin=True)
        data = login(client, "owner@example.com").json()["data"]
        assert data["churches"] == [] and data["active_church"] is None
        assert data["user"]["is_platform_admin"] is True
        assert client.get(ANY_ROLE, headers=bearer(data["access_token"])).status_code == 403
        assert client.get(ADMIN_ONLY, headers=bearer(data["access_token"])).status_code == 403


# --------------------------------------------------------- token validation

class TestTokenValidation:
    @pytest.fixture()
    def admin(self, session):
        church = make_church(session)
        user = make_user(session, "admin@example.com")
        membership = make_membership(session, church, user, "church_admin")
        return church, user, membership

    def test_no_token_is_401(self, client):
        assert client.get(ANY_ROLE).status_code == 401

    def test_garbage_token_is_401(self, client):
        assert client.get(ANY_ROLE, headers=bearer("not.a.jwt")).status_code == 401

    def test_token_signed_with_another_key_is_401(self, client, admin):
        church, user, _ = admin
        token = forge({"sub": str(user.id), "church_id": str(church.id)}, secret="some-other-secret")
        assert client.get(ANY_ROLE, headers=bearer(token)).status_code == 401

    def test_expired_token_is_401(self, client, admin):
        church, user, _ = admin
        token = forge({"sub": str(user.id), "church_id": str(church.id)}, exp=datetime.now(timezone.utc) - timedelta(seconds=5))
        assert client.get(ANY_ROLE, headers=bearer(token)).status_code == 401

    @pytest.mark.parametrize("sub", ["not-a-uuid", "", None])
    def test_bad_subject_is_401_not_500(self, client, admin, sub):
        church, _, _ = admin
        claims = {"church_id": str(church.id)} if sub is None else {"sub": sub, "church_id": str(church.id)}
        assert client.get(ANY_ROLE, headers=bearer(forge(claims))).status_code == 401

    def test_bad_church_id_is_401_not_500(self, client, admin):
        _, user, _ = admin
        assert client.get(ANY_ROLE, headers=bearer(forge({"sub": str(user.id), "church_id": "nope"}))).status_code == 401

    def test_validly_signed_token_for_a_church_the_user_is_not_in_is_401(self, client, session, admin):
        _, user, _ = admin
        other = make_church(session)
        token = forge({"sub": str(user.id), "church_id": str(other.id), "role": "church_admin"})
        assert client.get(ANY_ROLE, headers=bearer(token)).status_code == 401

    def test_deactivated_membership_locks_out_a_live_token(self, client, session, admin):
        _, _, membership = admin
        token = login(client, "admin@example.com").json()["data"]["access_token"]
        assert client.get(ANY_ROLE, headers=bearer(token)).status_code == 200
        membership.is_active = False
        session.flush()
        response = client.get(ANY_ROLE, headers=bearer(token))
        assert response.status_code == 401
        assert "no longer active" in response.json()["detail"]

    def test_deactivated_user_locks_out_a_live_token(self, client, session, admin):
        _, user, _ = admin
        token = login(client, "admin@example.com").json()["data"]["access_token"]
        user.is_active = False
        session.flush()
        assert client.get(ANY_ROLE, headers=bearer(token)).status_code == 401

    def test_role_comes_from_the_database_not_the_token(self, client, session, admin):
        _, _, membership = admin
        token = login(client, "admin@example.com").json()["data"]["access_token"]
        assert claims_of(token)["role"] == "church_admin"
        assert client.get(ADMIN_ONLY, headers=bearer(token)).status_code == 200
        membership.role = "secretary"  # demoted after the token was issued
        session.flush()
        assert client.get(ADMIN_ONLY, headers=bearer(token)).status_code == 403

    def test_a_token_cannot_claim_a_role_it_does_not_have(self, client, session):
        church = make_church(session)
        user = make_user(session, "sec@example.com")
        make_membership(session, church, user, "secretary")
        token = forge({"sub": str(user.id), "church_id": str(church.id), "role": "church_admin"})
        assert client.get(ADMIN_ONLY, headers=bearer(token)).status_code == 403


# ---------------------------------------------------------- switching church

class TestSwitchChurch:
    @pytest.fixture()
    def two_churches(self, session):
        a, b = make_church(session, "alpha-church"), make_church(session, "beta-church")
        user = make_user(session, "multi@example.com")
        make_membership(session, a, user, "church_admin")
        make_membership(session, b, user, "finance")
        return a, b, user

    def switch(self, client, token, church_id):
        return client.post("/api/v1/auth/switch-church", json={"church_id": str(church_id)}, headers=bearer(token))

    def test_church_less_token_can_pick_a_church(self, client, two_churches):
        a, _, _ = two_churches
        token = login(client, "multi@example.com").json()["data"]["access_token"]
        response = self.switch(client, token, a.id)
        assert response.status_code == 200
        new_token = response.json()["data"]["access_token"]
        assert claims_of(new_token)["church_id"] == str(a.id)
        assert client.get(ADMIN_ONLY, headers=bearer(new_token)).status_code == 200

    def test_switching_changes_the_role_and_old_token_keeps_its_church(self, client, two_churches):
        a, b, _ = two_churches
        token_a = self.switch(client, login(client, "multi@example.com").json()["data"]["access_token"], a.id).json()["data"]["access_token"]
        data_b = self.switch(client, token_a, b.id).json()["data"]
        token_b = data_b["access_token"]
        assert data_b["active_church"]["role"] == "finance"
        assert claims_of(token_b)["role"] == "finance"
        assert client.get(ADMIN_ONLY, headers=bearer(token_b)).status_code == 403  # only finance in B
        assert client.get(ADMIN_ONLY, headers=bearer(token_a)).status_code == 200  # still admin in A

    @pytest.mark.parametrize("kind", ["not_a_member", "nonexistent", "inactive_membership", "closed_church"])
    def test_cannot_switch_into_a_church_without_active_access(self, client, session, two_churches, kind):
        a, _, user = two_churches
        token = login(client, "multi@example.com").json()["data"]["access_token"]
        if kind == "not_a_member":
            target = make_church(session).id
        elif kind == "nonexistent":
            target = "00000000-0000-0000-0000-000000000000"
        elif kind == "inactive_membership":
            target = make_church(session)
            make_membership(session, target, user, "secretary", is_active=False)
            target = target.id
        else:
            a.status = "closed"
            session.flush()
            target = a.id
        response = self.switch(client, token, target)
        assert response.status_code == 403
        assert response.json()["detail"] == "You do not have access to that church"  # identical for every case

    def test_switch_requires_a_valid_token(self, client, two_churches):
        a, _, _ = two_churches
        assert client.post("/api/v1/auth/switch-church", json={"church_id": str(a.id)}).status_code == 401

    def test_list_my_churches(self, client, session, two_churches):
        make_church(session, "gamma-church")  # unrelated church must not appear
        token = login(client, "multi@example.com").json()["data"]["access_token"]
        response = client.get("/api/v1/auth/churches", headers=bearer(token))
        assert [c["slug"] for c in response.json()["data"]] == ["alpha-church", "beta-church"]

    def test_me_reports_the_active_church_or_none(self, client, session, two_churches):
        a, _, _ = two_churches
        church_less = login(client, "multi@example.com").json()["data"]["access_token"]
        assert client.get("/api/v1/auth/me", headers=bearer(church_less)).json()["data"]["active_church"] is None
        token = self.switch(client, church_less, a.id).json()["data"]["access_token"]
        me = client.get("/api/v1/auth/me", headers=bearer(token)).json()["data"]
        assert me["active_church"]["id"] == str(a.id) and me["role"] == "church_admin"


# ------------------------------------------------------------ role enforcement

class TestRoles:
    @pytest.mark.parametrize("role,status_code", [("church_admin", 200), ("secretary", 403), ("finance", 403), ("group_leader", 403), ("member", 403)])
    def test_admin_only_endpoint(self, client, session, role, status_code):
        make_membership(session, make_church(session), make_user(session, "u@example.com"), role)
        token = login(client, "u@example.com").json()["data"]["access_token"]
        assert client.get(ADMIN_ONLY, headers=bearer(token)).status_code == status_code

    def test_old_superadmin_role_is_gone(self, session):
        from app.models import Membership
        from tests.helpers import rejected_by
        with rejected_by(session, "ck_memberships_role"):
            make_membership(session, make_church(session), make_user(session), "superadmin")


# ------------------------------------------------------------ platform admin

class TestPlatformAdminDependency:
    """No route uses it yet (Phase 5), so mount one on a throwaway app."""

    @pytest.fixture()
    def pa_client(self, session):
        app = FastAPI()

        @app.get("/platform-only")
        def platform_only(context: CurrentUser = Depends(require_platform_admin)):
            return {"email": context.email}

        app.dependency_overrides[get_db] = lambda: session
        return TestClient(app)

    def test_platform_admin_allowed_even_without_a_church(self, pa_client, client, session):
        make_user(session, "owner@example.com", is_platform_admin=True)
        token = login(client, "owner@example.com").json()["data"]["access_token"]
        assert pa_client.get("/platform-only", headers=bearer(token)).json() == {"email": "owner@example.com"}

    def test_church_admin_is_not_a_platform_admin(self, pa_client, client, session):
        make_membership(session, make_church(session), make_user(session, "admin@example.com"), "church_admin")
        token = login(client, "admin@example.com").json()["data"]["access_token"]
        assert pa_client.get("/platform-only", headers=bearer(token)).status_code == 403

    def test_flag_is_read_from_the_database_not_the_token(self, pa_client, client, session):
        user = make_user(session, "owner@example.com", is_platform_admin=True)
        token = login(client, "owner@example.com").json()["data"]["access_token"]
        user.is_platform_admin = False
        session.flush()
        assert pa_client.get("/platform-only", headers=bearer(token)).status_code == 403

    def test_a_forged_platform_claim_does_nothing(self, pa_client, client, session):
        user = make_user(session, "plain@example.com")
        token = forge({"sub": str(user.id), "is_platform_admin": True, "role": "platform_admin"})
        assert pa_client.get("/platform-only", headers=bearer(token)).status_code == 403


# -------------------------------------------------------------- change password

class TestChangePassword:
    @pytest.fixture()
    def signed_in(self, client, session):
        make_membership(session, make_church(session), make_user(session, "pw@example.com"), "secretary")
        return login(client, "pw@example.com").json()["data"]["access_token"]

    def change(self, client, token, current=DEFAULT_PASSWORD, new="a-brand-new-password"):
        return client.post(
            "/api/v1/auth/change-password",
            json={"current_password": current, "new_password": new},
            headers=bearer(token),
        )

    def test_success_invalidates_old_tokens_and_returns_a_fresh_one(self, client, signed_in):
        response = self.change(client, signed_in)
        assert response.status_code == 200
        fresh = response.json()["data"]["access_token"]
        assert claims_of(fresh)["church_id"] == claims_of(signed_in)["church_id"]
        assert client.get(ANY_ROLE, headers=bearer(signed_in)).status_code == 401  # old session ended
        assert client.get(ANY_ROLE, headers=bearer(fresh)).status_code == 200
        assert login(client, "pw@example.com", "a-brand-new-password").status_code == 200
        assert login(client, "pw@example.com", DEFAULT_PASSWORD).status_code == 401

    def test_wrong_current_password(self, client, signed_in):
        assert self.change(client, signed_in, current="not-it").status_code == 400
        assert client.get(ANY_ROLE, headers=bearer(signed_in)).status_code == 200  # nothing changed

    @pytest.mark.parametrize("new", ["short", "x" * 73])
    def test_new_password_length_limits(self, client, signed_in, new):
        assert self.change(client, signed_in, new=new).status_code == 422

    def test_works_for_a_church_less_token_too(self, client, session):
        a, b = make_church(session), make_church(session)
        user = make_user(session, "multi@example.com")
        make_membership(session, a, user)
        make_membership(session, b, user)
        token = login(client, "multi@example.com").json()["data"]["access_token"]
        assert self.change(client, token).status_code == 200
