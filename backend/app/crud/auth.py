from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.models.church import Church
from app.models.membership import Membership
from app.models.password_reset import PasswordResetToken
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, *, email: str, password: str, is_platform_admin: bool = False) -> User:
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        is_platform_admin=is_platform_admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


_DUMMY_HASH = hash_password("not-a-real-password")


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        verify_password(password, _DUMMY_HASH)  # same work as a real check, so timing does not reveal the account
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


# --------------------------------------------------------------- church access

def list_church_access(db: Session, user_id: UUID) -> list[tuple[Membership, Church]]:
    """Active memberships in churches that are not closed, ordered by church name."""
    return (
        db.query(Membership, Church)
        .execution_options(skip_tenant_scope=True)  # spans the user's churches
        .join(Church, Church.id == Membership.church_id)
        .filter(Membership.user_id == user_id, Membership.is_active.is_(True), Church.status != "closed")
        .order_by(Church.name.asc())
        .all()
    )


def get_church_access(db: Session, user_id: UUID, church_id: UUID) -> tuple[Membership, Church] | None:
    return (
        db.query(Membership, Church)
        .execution_options(skip_tenant_scope=True)  # spans the user's churches
        .join(Church, Church.id == Membership.church_id)
        .filter(
            Membership.user_id == user_id,
            Membership.church_id == church_id,
            Membership.is_active.is_(True),
            Church.status != "closed",
        )
        .first()
    )


# -------------------------------------------------------------------- passwords

def _set_password(user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)
    # Invalidates every token issued before this moment (checked in get_session_context).
    user.password_changed_at = _now()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    if not verify_password(current_password, user.hashed_password):
        return False
    _set_password(user, new_password)
    db.commit()
    return True


def request_password_reset(db: Session, email: str, expires_minutes: int) -> tuple[User, str] | None:
    """Create a reset token for an active user. Returns ``(user, raw_token)`` or ``None``.

    Any earlier unused tokens for the user are revoked, so only the latest link works.
    """
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    now = _now()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    raw, hashed = generate_token()
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashed, expires_at=now + timedelta(minutes=expires_minutes)))
    db.commit()
    return user, raw


def reset_password(db: Session, raw_token: str, new_password: str) -> bool:
    """Consume a reset token and set the password. False if unknown, used, expired or inactive."""
    now = _now()
    token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(raw_token))
        .with_for_update()
        .first()
    )
    if token is None or token.used_at is not None or token.expires_at <= now:
        return False
    user = get_user_by_id(db, token.user_id)
    if user is None or not user.is_active:
        return False
    _set_password(user, new_password)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    return True
