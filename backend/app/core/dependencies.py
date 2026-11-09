"""Authentication and authorisation dependencies.

Three layers, from weakest to strongest guarantee:

* ``get_token_claims``    - a validly signed, unexpired JWT.
* ``get_session_context`` - the user is real, active, and the token was not issued before
                            a password change. If the token names a church, the user has an
                            ACTIVE membership there. A church is optional (the token issued
                            to a multi-church user at login has none).
* ``get_current_user``    - same, but a church is REQUIRED. Every tenant endpoint uses this
                            (directly or via ``require_roles``).

The role and branch always come from the user's membership row in the database, never
from the token, so demoting or removing someone takes effect on their next request.
"""
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import get_db
from app.db.tenancy import bind_tenant, clear_tenant
from app.models.church import Branch, Church
from app.models.membership import Membership
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )


def _parse_uuid(value) -> UUID | None:
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


@dataclass
class CurrentUser:
    """The authenticated user plus the church context of this request.

    Exposes ``id``, ``email``, ``role``, ``member_id``, ``church_id`` and ``branch_id`` so
    endpoint code written against the old single-church ``User`` keeps working. ``role``,
    ``member_id``, ``church_id`` and ``branch_id`` are ``None`` until a church is selected.
    """

    user: User
    membership: Membership | None = None
    church: Church | None = None

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def email(self) -> str:
        return self.user.email

    @property
    def is_platform_admin(self) -> bool:
        return bool(self.user.is_platform_admin)

    @property
    def role(self) -> str | None:
        return self.membership.role if self.membership else None

    @property
    def member_id(self) -> UUID | None:
        return self.membership.member_id if self.membership else None

    @property
    def church_id(self) -> UUID | None:
        return self.church.id if self.church else None

    @property
    def branch_id(self) -> UUID | None:
        return self.membership.branch_id if self.membership else None

    @property
    def is_branch_scoped(self) -> bool:
        return self.branch_id is not None


def get_token_claims(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return decode_token(token)
    except Exception as exc:  # bad signature, expired, malformed
        raise _unauthorized() from exc


def get_session_context(claims: dict = Depends(get_token_claims), db: Session = Depends(get_db)) -> CurrentUser:
    user_id = _parse_uuid(claims.get("sub"))
    if user_id is None:
        raise _unauthorized()
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise _unauthorized()

    # A password change/reset invalidates every token issued before it.
    if user.password_changed_at is not None:
        issued_at = claims.get("iat")
        if not isinstance(issued_at, (int, float)) or issued_at < user.password_changed_at.timestamp():
            raise _unauthorized("Session expired, please sign in again")

    raw_church_id = claims.get("church_id")
    if raw_church_id is None:
        clear_tenant(db)
        return CurrentUser(user=user)

    church_id = _parse_uuid(raw_church_id)
    if church_id is None:
        raise _unauthorized()
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == user.id,
            Membership.church_id == church_id,
            Membership.is_active.is_(True),
        )
        .first()
    )
    if membership is None:
        raise _unauthorized("Your access to this church is no longer active")
    church = db.query(Church).filter(Church.id == church_id).first()
    if church is None:  # cannot happen (FK), but never trust a token's word
        raise _unauthorized()
    if church.status == "closed":
        raise _unauthorized("This church account has been closed")
    main_branch_id = (
        db.query(Branch.id)
        .filter(Branch.church_id == church.id, Branch.is_main.is_(True))
        .scalar()
    )
    # From here on every ORM query on this session is limited to this church (and
    # branch, for branch-scoped memberships). See app/db/tenancy.py.
    bind_tenant(db, church.id, branch_id=membership.branch_id, default_branch_id=main_branch_id)
    return CurrentUser(user=user, membership=membership, church=church)


def get_current_user(context: CurrentUser = Depends(get_session_context)) -> CurrentUser:
    if context.church is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No church selected. Choose a church first.")
    return context


def get_current_church(current_user: CurrentUser = Depends(get_current_user)) -> Church:
    return current_user.church


def get_current_membership(current_user: CurrentUser = Depends(get_current_user)) -> Membership:
    return current_user.membership


def require_roles(*roles: str):
    """Allow only users whose role *in the active church* is one of ``roles``."""

    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return role_checker


def require_platform_admin(context: CurrentUser = Depends(get_session_context)) -> CurrentUser:
    """Product-owner operators only. Independent of any church membership."""
    if not context.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return context
