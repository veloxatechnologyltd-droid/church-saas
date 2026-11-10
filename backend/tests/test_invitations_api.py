"""Invitations: an admin invites an email into their church; the invitee redeems an emailed token."""
import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models import Invitation, Membership, User
from tests.helpers import (
    DEFAULT_PASSWORD, make_branch, make_church, make_member, make_membership, make_user,
)
from tests.test_auth_api import ANY_ROLE, bearer, login

INVITES = "/api/v1/invitations/"
NEW_PASSWORD = "freshly-chosen-pass"


def token_from(outbox, index=-1):
    match = re.search(r"token=([\w-]+)", outbox.outbox[index].body)
    assert match, outbox.outbox[index].body
    return match.group(1)


@pytest.fixture()
def church(session):
    return make_church(session, "grace-chapel")


@pytest.fixture()
def admin_token(client, session, church):
    make_membership(session, church, make_user(session, "admin@example.com"), "church_admin")
    return login(client, "admin@example.com").json()["data"]["access_token"]


def invite(client, token, **body):
    body.setdefault("email", "newbie@example.com")
    body.setdefault("role", "secretary")
    return client.post(INVITES, json=body, headers=bearer(token))


def accept(client, token, password=None):
    body = {"token": token}
    if password:
        body["password"] = password
    return client.post(f"{INVITES}accept", json=body)


# ------------------------------------------------------------------ creating

class TestCreate:
    def test_admin_invites_and_the_token_is_only_in_the_email(self, client, session, outbox, church, admin_token):
        response = invite(client, admin_token, email="  Newbie@Example.COM ", role="finance")

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["email"] == "newbie@example.com" and data["role"] == "finance" and data["email_sent"] is True
        raw = token_from(outbox)
        assert raw not in response.text  # never returned by the API
        assert len(outbox.outbox) == 1 and outbox.outbox[0].to == "newbie@example.com"
        assert "Grace Chapel" in outbox.outbox[0].subject
        assert "/accept-invite?token=" in outbox.outbox[0].body

        row = session.query(Invitation).one()
        assert row.church_id == church.id and row.token_hash != raw  # only a hash is stored
        assert raw not in session.execute(text("SELECT string_agg(i::text, ' ') FROM invitations i")).scalar()

    def test_the_invitation_is_audited(self, client, session, church, admin_token):
        from app.models import AuditLog
        invite(client, admin_token)
        log = session.query(AuditLog).filter_by(table_name="invitations", action="created").one()
        assert log.church_id == church.id and log.new_value["email"] == "newbie@example.com"

    @pytest.mark.parametrize("role", ["secretary", "finance", "group_leader", "member"])
    def test_only_church_admins_can_invite(self, client, session, church, role):
        make_membership(session, church, make_user(session, "staff@example.com"), role)
        token = login(client, "staff@example.com").json()["data"]["access_token"]
        assert invite(client, token).status_code == 403

    def test_requires_authentication(self, client):
        assert client.post(INVITES, json={"email": "a@b.co", "role": "member"}).status_code == 401

    @pytest.mark.parametrize("email", ["nope", "a@b", "a b@c.co", "@c.co", "a@@c.co"])
    def test_rejects_malformed_email(self, client, admin_token, email):
        assert invite(client, admin_token, email=email).status_code == 422

    @pytest.mark.parametrize("role", ["superadmin", "platform_admin", "root", ""])
    def test_rejects_unknown_roles(self, client, admin_token, role):
        assert invite(client, admin_token, role=role).status_code == 422

    def test_cannot_invite_someone_who_is_already_a_member(self, client, session, church, admin_token):
        make_membership(session, church, make_user(session, "already@example.com"), "member")
        assert invite(client, admin_token, email="already@example.com").status_code == 409

    def test_can_invite_someone_who_belongs_to_another_church(self, client, session, admin_token):
        make_membership(session, make_church(session), make_user(session, "elsewhere@example.com"), "member")
        assert invite(client, admin_token, email="elsewhere@example.com").status_code == 201

    def test_can_reinvite_a_deactivated_member(self, client, session, church, admin_token):
        make_membership(session, church, make_user(session, "former@example.com"), "member", is_active=False)
        assert invite(client, admin_token, email="former@example.com").status_code == 201

    def test_reinviting_revokes_the_earlier_link(self, client, outbox, admin_token):
        invite(client, admin_token)
        first = token_from(outbox)
        invite(client, admin_token, role="finance")
        second = token_from(outbox)
        assert first != second
        assert accept(client, first, NEW_PASSWORD).status_code == 400
        assert accept(client, second, NEW_PASSWORD).status_code == 200

    def test_invited_branch_must_belong_to_this_church(self, client, session, admin_token):
        foreign = make_branch(session, make_church(session))
        response = invite(client, admin_token, branch_id=str(foreign.id))
        assert response.status_code == 400 and "Branch not found" in response.json()["detail"]

    def test_inactive_branch_is_refused(self, client, session, church, admin_token):
        branch = make_branch(session, church)
        branch.is_active = False
        session.flush()
        assert invite(client, admin_token, branch_id=str(branch.id)).status_code == 400

    def test_linked_member_profile_must_belong_to_this_church(self, client, session, church, admin_token):
        foreign = make_member(session, make_church(session))
        assert invite(client, admin_token, member_id=str(foreign.id)).status_code == 400
        own = make_member(session, church)
        assert invite(client, admin_token, member_id=str(own.id)).status_code == 201

    def test_email_delivery_failure_does_not_lose_the_invitation(self, client, session, outbox, admin_token):
        def boom(message):
            raise RuntimeError("smtp down")
        outbox.send = boom
        response = invite(client, admin_token)
        assert response.status_code == 201 and response.json()["data"]["email_sent"] is False
        assert session.query(Invitation).count() == 1


# ----------------------------------------------------------- branch-scoped admin

class TestBranchScopedAdmin:
    @pytest.fixture()
    def setup(self, client, session, church):
        east, west = make_branch(session, church, "East"), make_branch(session, church, "West")
        make_membership(session, church, make_user(session, "eastadmin@example.com"), "church_admin", branch_id=east.id)
        make_membership(session, church, make_user(session, "chief@example.com"), "church_admin")
        token = login(client, "eastadmin@example.com").json()["data"]["access_token"]
        return east, west, token, login(client, "chief@example.com").json()["data"]["access_token"]

    def test_invites_default_to_their_own_branch(self, client, session, setup):
        east, _, token, _ = setup
        assert invite(client, token).json()["data"]["branch_id"] == str(east.id)

    def test_cannot_invite_into_another_branch(self, client, setup):
        _, west, token, _ = setup
        assert invite(client, token, branch_id=str(west.id)).status_code == 403

    def test_sees_and_revokes_only_their_branchs_invitations(self, client, session, setup):
        east, west, token, chief = setup
        mine = invite(client, token, email="a@example.com").json()["data"]["id"]
        theirs = invite(client, chief, email="b@example.com", branch_id=str(west.id)).json()["data"]["id"]
        church_wide = invite(client, chief, email="c@example.com").json()["data"]["id"]

        listed = {row["id"] for row in client.get(INVITES, headers=bearer(token)).json()["data"]}
        assert listed == {mine}
        assert client.delete(f"{INVITES}{theirs}", headers=bearer(token)).status_code == 404
        assert client.delete(f"{INVITES}{church_wide}", headers=bearer(token)).status_code == 404
        assert client.delete(f"{INVITES}{mine}", headers=bearer(token)).status_code == 204
        assert {row["id"] for row in client.get(INVITES, headers=bearer(chief)).json()["data"]} == {theirs, church_wide}


# --------------------------------------------------------------- listing / revoking

class TestListAndRevoke:
    def test_lists_pending_only(self, client, outbox, admin_token):
        keep = invite(client, admin_token, email="keep@example.com").json()["data"]["id"]
        gone = invite(client, admin_token, email="gone@example.com").json()["data"]["id"]
        used = invite(client, admin_token, email="used@example.com")
        accept(client, token_from(outbox), NEW_PASSWORD)
        client.delete(f"{INVITES}{gone}", headers=bearer(admin_token))

        listed = client.get(INVITES, headers=bearer(admin_token)).json()
        assert [row["id"] for row in listed["data"]] == [keep] and listed["total"] == 1

    def test_revoked_invitation_cannot_be_redeemed(self, client, outbox, admin_token):
        row = invite(client, admin_token).json()["data"]
        assert client.delete(f"{INVITES}{row['id']}", headers=bearer(admin_token)).status_code == 204
        assert accept(client, token_from(outbox), NEW_PASSWORD).status_code == 400

    def test_each_church_sees_only_its_own_invitations(self, client, session, admin_token):
        other = make_church(session)
        make_membership(session, other, make_user(session, "otheradmin@example.com"), "church_admin")
        other_token = login(client, "otheradmin@example.com").json()["data"]["access_token"]
        mine = invite(client, admin_token, email="mine@example.com").json()["data"]["id"]
        theirs = invite(client, other_token, email="theirs@example.com").json()["data"]["id"]

        assert [r["id"] for r in client.get(INVITES, headers=bearer(admin_token)).json()["data"]] == [mine]
        assert [r["id"] for r in client.get(INVITES, headers=bearer(other_token)).json()["data"]] == [theirs]

    def test_cannot_revoke_another_churchs_invitation(self, client, session, admin_token):
        other = make_church(session)
        make_membership(session, other, make_user(session, "otheradmin@example.com"), "church_admin")
        other_token = login(client, "otheradmin@example.com").json()["data"]["access_token"]
        theirs = invite(client, other_token, email="theirs@example.com").json()["data"]["id"]

        assert client.delete(f"{INVITES}{theirs}", headers=bearer(admin_token)).status_code == 404
        assert len(client.get(INVITES, headers=bearer(other_token)).json()["data"]) == 1  # still pending

    def test_revoking_something_unknown_is_404(self, client, admin_token):
        assert client.delete(f"{INVITES}00000000-0000-0000-0000-000000000000", headers=bearer(admin_token)).status_code == 404


# ------------------------------------------------------------------- redeeming

class TestAccept:
    def test_new_person_creates_an_account_with_the_offered_role_and_branch(self, client, session, outbox, church, admin_token):
        branch = make_branch(session, church)
        member = make_member(session, church)
        invite(client, admin_token, role="group_leader", branch_id=str(branch.id), member_id=str(member.id))

        response = accept(client, token_from(outbox), NEW_PASSWORD)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["account_created"] is True and data["role"] == "group_leader"
        assert data["church"]["slug"] == "grace-chapel"
        assert "access_token" not in response.text  # redeeming does not sign anyone in
        user = session.query(User).filter_by(email="newbie@example.com").one()
        membership = session.query(Membership).filter_by(user_id=user.id, church_id=church.id).one()
        assert (membership.role, membership.branch_id, membership.member_id) == ("group_leader", branch.id, member.id)
        login_data = login(client, "newbie@example.com", NEW_PASSWORD).json()["data"]
        assert login_data["active_church"]["role"] == "group_leader"

    def test_a_password_is_required_for_a_new_account(self, client, session, outbox, admin_token):
        invite(client, admin_token)
        raw = token_from(outbox)
        assert accept(client, raw).status_code == 422
        assert session.query(User).filter_by(email="newbie@example.com").count() == 0
        assert accept(client, raw, NEW_PASSWORD).status_code == 200  # the failed attempt did not burn the link

    @pytest.mark.parametrize("password", ["short", "x" * 73])
    def test_password_length_limits(self, client, outbox, admin_token, password):
        invite(client, admin_token)
        assert accept(client, token_from(outbox), password).status_code == 422

    def test_existing_account_gets_the_membership_and_keeps_its_password(self, client, session, outbox, church, admin_token):
        other = make_church(session, "other-church")
        user = make_user(session, "newbie@example.com", password="my-old-password")
        make_membership(session, other, user, "member")
        old_hash = user.hashed_password

        invite(client, admin_token, role="finance")
        raw = token_from(outbox)
        # Without the account's own password nothing happens (anti pre-hijack) and the link stays usable.
        needs = accept(client, raw)
        assert needs.status_code == 422 and needs.json()["detail"]["code"] == "existing_account"
        assert accept(client, raw, "wrong-password-1").status_code == 400
        response = accept(client, raw, "my-old-password")

        assert response.status_code == 200 and response.json()["data"]["account_created"] is False
        session.refresh(user)
        assert user.hashed_password == old_hash  # a stranger's emailed link cannot reset a password
        data = login(client, "newbie@example.com", "my-old-password").json()["data"]
        assert {c["slug"] for c in data["churches"]} == {"grace-chapel", "other-church"}
        assert login(client, "newbie@example.com", "ignored-new-password").status_code == 401

    def test_an_attacker_owned_account_cannot_inherit_the_invitation(self, client, session, outbox, church, admin_token):
        """Someone registered the victim's email first with their own password. The victim, who
        holds the emailed link but not that password, cannot attach the church to that account."""
        attacker_account = make_user(session, "newbie@example.com", password="attacker-chosen-pw")
        invite(client, admin_token)
        assert accept(client, token_from(outbox), "victim-guess-1").status_code == 400
        assert session.query(Membership).filter_by(user_id=attacker_account.id, church_id=church.id).count() == 0

    def test_a_previously_removed_member_is_reactivated_with_the_new_role(self, client, session, outbox, church, admin_token):
        user = make_user(session, "newbie@example.com")
        old = make_membership(session, church, user, "member", is_active=False)
        invite(client, admin_token, role="secretary")
        assert accept(client, token_from(outbox), "correct-horse-battery").status_code == 200
        session.refresh(old)
        assert old.is_active is True and old.role == "secretary"
        assert session.query(Membership).filter_by(user_id=user.id, church_id=church.id).count() == 1

    def test_single_use(self, client, outbox, admin_token):
        invite(client, admin_token)
        raw = token_from(outbox)
        assert accept(client, raw, NEW_PASSWORD).status_code == 200
        second = accept(client, raw, NEW_PASSWORD)
        assert second.status_code == 400 and "invalid or has expired" in second.json()["detail"]

    def test_expired(self, client, session, outbox, admin_token):
        invite(client, admin_token)
        session.query(Invitation).update({Invitation.expires_at: datetime.now(timezone.utc) - timedelta(seconds=1)})
        session.flush()
        assert accept(client, token_from(outbox), NEW_PASSWORD).status_code == 400

    def test_default_lifetime_matches_the_setting(self, client, session, admin_token):
        invite(client, admin_token)
        row = session.query(Invitation).one()
        hours = (row.expires_at - datetime.now(timezone.utc)).total_seconds() / 3600
        assert 167 < hours <= 168

    @pytest.mark.parametrize("token", ["", "garbage", "x" * 500])
    def test_unknown_tokens_get_the_same_error_as_expired_ones(self, client, token):
        response = client.post(f"{INVITES}accept", json={"token": token, "password": NEW_PASSWORD})
        assert response.status_code in (400, 422)
        if response.status_code == 400:
            assert response.json()["detail"] == "This invitation is invalid or has expired"

    def test_inactive_account_cannot_redeem(self, client, session, outbox, admin_token):
        make_user(session, "newbie@example.com", is_active=False)
        invite(client, admin_token)
        assert accept(client, token_from(outbox), NEW_PASSWORD).status_code == 400
        assert session.query(Membership).count() == 1  # only the admin's

    def test_redeeming_is_audited_in_the_invited_church(self, client, session, outbox, church, admin_token):
        from app.models import AuditLog
        invite(client, admin_token)
        accept(client, token_from(outbox), NEW_PASSWORD)
        log = session.query(AuditLog).filter_by(table_name="invitations", action="accepted").one()
        assert log.church_id == church.id and log.user_id is not None

    def test_new_member_only_ever_sees_the_church_that_invited_them(self, client, session, outbox, church, admin_token):
        make_church(session, "someone-elses")
        invite(client, admin_token)
        accept(client, token_from(outbox), NEW_PASSWORD)
        data = login(client, "newbie@example.com", NEW_PASSWORD).json()["data"]
        assert [c["slug"] for c in data["churches"]] == ["grace-chapel"]
        assert client.get(ANY_ROLE, headers=bearer(data["access_token"])).status_code == 200
