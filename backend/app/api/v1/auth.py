import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import CurrentUser, get_session_context
from app.core.security import create_access_token
from app.crud import auth as auth_crud
from app.db.database import get_db
from app.models.church import Church
from app.models.membership import Membership
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChurchAccess,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SwitchChurchRequest,
)
from app.services.email import EmailSender, get_email_sender, password_reset_email

logger = logging.getLogger(__name__)
router = APIRouter()


def _issue_token(user: User, membership: Membership | None = None) -> str:
    """JWT with ``sub`` and, when a church is selected, ``church_id``, ``role`` and ``branch_id``.

    The server re-reads role and branch from the membership on every request; the claims
    are for clients, not for authorisation.
    """
    claims: dict = {"sub": str(user.id)}
    if membership is not None:
        claims["church_id"] = str(membership.church_id)
        claims["role"] = membership.role
        if membership.branch_id is not None:
            claims["branch_id"] = str(membership.branch_id)
    return create_access_token(claims)


def _church_access(membership: Membership, church: Church) -> dict:
    return ChurchAccess(
        id=church.id,
        name=church.name,
        slug=church.slug,
        logo_url=church.logo_url,
        status=church.status,
        role=membership.role,
        branch_id=membership.branch_id,
    ).model_dump(mode="json")


def _user_payload(context: CurrentUser) -> dict:
    """Shape kept compatible with the single-church API (role/member_id of the active church)."""
    user = context.user
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "is_platform_admin": bool(user.is_platform_admin),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "role": context.role,
        "member_id": str(context.member_id) if context.member_id else None,
        "church_id": str(context.church_id) if context.church_id else None,
        "branch_id": str(context.branch_id) if context.branch_id else None,
    }


def _active_church(context: CurrentUser) -> dict | None:
    return _church_access(context.membership, context.church) if context.church else None


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_crud.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access = auth_crud.list_church_access(db, user.id)
    if not access and not user.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is not a member of any church")

    # One church: sign straight in. Several: a church-less token that can only list and switch.
    selected = access[0] if len(access) == 1 else None
    membership, church = selected if selected else (None, None)
    context = CurrentUser(user=user, membership=membership, church=church)
    return {
        "status": "success",
        "data": {
            "access_token": _issue_token(user, membership),
            "token_type": "bearer",
            "user": _user_payload(context),
            "churches": [_church_access(m, c) for m, c in access],
            "active_church": _active_church(context),
        },
    }


@router.get("/churches")
def my_churches(context: CurrentUser = Depends(get_session_context), db: Session = Depends(get_db)):
    access = auth_crud.list_church_access(db, context.id)
    return {
        "status": "success",
        "data": [_church_access(m, c) for m, c in access],
        "total": len(access),
    }


@router.post("/switch-church")
def switch_church(
    payload: SwitchChurchRequest,
    context: CurrentUser = Depends(get_session_context),
    db: Session = Depends(get_db),
):
    access = auth_crud.get_church_access(db, context.id, payload.church_id)
    if access is None:
        # Same answer whether the church does not exist or the user is not in it.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to that church")
    membership, church = access
    new_context = CurrentUser(user=context.user, membership=membership, church=church)
    return {
        "status": "success",
        "data": {
            "access_token": _issue_token(context.user, membership),
            "token_type": "bearer",
            "user": _user_payload(new_context),
            "active_church": _active_church(new_context),
        },
    }


@router.get("/me")
def me(context: CurrentUser = Depends(get_session_context)):
    return {
        "status": "success",
        "data": {**_user_payload(context), "active_church": _active_church(context)},
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    context: CurrentUser = Depends(get_session_context),
):
    changed = auth_crud.change_password(db, context.user, payload.current_password, payload.new_password)
    if not changed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Every older token is now invalid (including the caller's), so hand back a fresh one.
    return {
        "status": "success",
        "data": {
            "message": "Password changed successfully",
            "access_token": _issue_token(context.user, context.membership),
            "token_type": "bearer",
        },
    }


_FORGOT_PASSWORD_REPLY = {
    "status": "success",
    "data": {"message": "If that email belongs to an account, a reset link has been sent."},
}


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    """Always answers the same way, so it cannot be used to discover which emails have accounts."""
    created = auth_crud.request_password_reset(db, payload.email, settings.PASSWORD_RESET_EXPIRE_MINUTES)
    if created is not None:
        user, raw_token = created
        link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={raw_token}"
        try:
            sender.send(
                password_reset_email(
                    to=user.email, link=link, expires_minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
                )
            )
        except Exception:  # the reply must not depend on whether delivery worked
            logger.exception("Could not send password reset email")
    return _FORGOT_PASSWORD_REPLY


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not auth_crud.reset_password(db, payload.token, payload.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired")
    return {"status": "success", "data": {"message": "Password updated. You can now sign in."}}
