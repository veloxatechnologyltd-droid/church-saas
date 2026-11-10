"""Church invitations. Every function takes the church explicitly and filters on it."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.models.church import Branch, Church
from app.models.invitation import Invitation
from app.models.member import Member
from app.models.membership import Membership
from app.models.user import User
from app.services.audit import record_audit


class InvitationInvalid(Exception):
    """Unknown, expired, revoked or already used (deliberately one error: no probing)."""


class PasswordRequired(Exception):
    """The invited email has no account yet, so a password must be chosen."""


class ExistingAccountPasswordRequired(Exception):
    """The email already has an account: its owner must prove it with their current password."""


class WrongPassword(Exception):
    """The current password given for an existing account is wrong."""


class AlreadyMember(Exception):
    """The email already belongs to an active member of the church."""


def branch_is_active_in_church(db: Session, church_id: UUID, branch_id: UUID) -> bool:
    return (
        db.query(Branch.id)
        .filter(Branch.id == branch_id, Branch.church_id == church_id, Branch.is_active.is_(True))
        .first()
        is not None
    )


def member_exists_in_church(db: Session, church_id: UUID, member_id: UUID) -> bool:
    return db.query(Member.id).filter(Member.id == member_id, Member.church_id == church_id).first() is not None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _find_user(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def _membership(db: Session, user_id: UUID, church_id: UUID) -> Membership | None:
    return (
        db.query(Membership)
        .execution_options(skip_tenant_scope=True)  # accepting an invite may target another church
        .filter(Membership.user_id == user_id, Membership.church_id == church_id)
        .first()
    )


def create_invitation(
    db: Session,
    *,
    church_id: UUID,
    invited_by: UUID,
    email: str,
    role: str,
    branch_id: UUID | None,
    member_id: UUID | None,
    expires_hours: int,
) -> tuple[Invitation, str]:
    """Create an invitation, revoking any pending one for the same email. Returns ``(row, raw_token)``."""
    existing_user = _find_user(db, email)
    if existing_user is not None:
        current = _membership(db, existing_user.id, church_id)
        if current is not None and current.is_active:
            raise AlreadyMember()

    now = _now()
    db.query(Invitation).filter(
        Invitation.church_id == church_id,
        Invitation.email == email,
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
    ).update({Invitation.revoked_at: now}, synchronize_session=False)

    raw, hashed = generate_token()
    invitation = Invitation(
        church_id=church_id,
        email=email,
        role=role,
        branch_id=branch_id,
        member_id=member_id,
        token_hash=hashed,
        invited_by=invited_by,
        expires_at=now + timedelta(hours=expires_hours),
    )
    db.add(invitation)
    db.flush()  # the caller records the audit row and commits, so both land together
    db.refresh(invitation)
    return invitation, raw


def list_pending(db: Session, church_id: UUID, branch_id: UUID | None = None) -> list[Invitation]:
    query = db.query(Invitation).filter(
        Invitation.church_id == church_id,
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
    )
    if branch_id is not None:
        query = query.filter(Invitation.branch_id == branch_id)
    return query.order_by(Invitation.created_at.desc()).all()


def get_pending(db: Session, church_id: UUID, invitation_id: UUID) -> Invitation | None:
    return (
        db.query(Invitation)
        .filter(
            Invitation.id == invitation_id,
            Invitation.church_id == church_id,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .first()
    )


def revoke(db: Session, invitation: Invitation) -> None:
    invitation.revoked_at = _now()
    db.flush()


def accept(db: Session, raw_token: str, password: str | None) -> tuple[Invitation, bool]:
    """Redeem an invitation. Returns ``(invitation, account_was_created)``.

    The invitation row is locked, so two simultaneous redemptions cannot both succeed.
    A new account is created with the chosen password. An existing account must present its
    own current password; it then receives the membership (its password is untouched and no
    session is issued).
    """
    now = _now()
    invitation = (
        db.query(Invitation)
        .filter(Invitation.token_hash == hash_token(raw_token))
        .with_for_update()
        .first()
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= now
    ):
        raise InvitationInvalid()
    # A closed church accepts no new people (its data is waiting to be deleted).
    if db.query(Church.status).filter(Church.id == invitation.church_id).scalar() == "closed":
        raise InvitationInvalid()

    user = _find_user(db, invitation.email)
    created = False
    if user is None:
        if not password:
            raise PasswordRequired()
        user = User(email=invitation.email, hashed_password=hash_password(password), is_active=True)
        db.add(user)
        db.flush()
        created = True
    elif not user.is_active:
        raise InvitationInvalid()
    else:
        # An account for this email exists. Holding the emailed link proves control of the mailbox,
        # but not of the account (someone else may have registered it first with their own password),
        # so the account's own password is required before it receives this church's access.
        if not password:
            raise ExistingAccountPasswordRequired()
        if not verify_password(password, user.hashed_password):
            raise WrongPassword()

    membership = _membership(db, user.id, invitation.church_id)
    if membership is None:
        db.add(
            Membership(
                church_id=invitation.church_id,
                user_id=user.id,
                role=invitation.role,
                branch_id=invitation.branch_id,
                member_id=invitation.member_id,
            )
        )
    else:  # previously removed from this church: re-activate with the newly offered access
        membership.is_active = True
        membership.role = invitation.role
        membership.branch_id = invitation.branch_id
        membership.member_id = invitation.member_id

    invitation.accepted_at = now
    record_audit(
        db,
        church_id=invitation.church_id,
        user_id=user.id,
        action="accepted",
        table_name="invitations",
        record_id=invitation.id,
        new_value={"role": invitation.role, "branch_id": str(invitation.branch_id) if invitation.branch_id else None},
    )
    db.commit()
    return invitation, created
