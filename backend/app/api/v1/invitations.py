import logging
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.middleware import limiter
from app.core.dependencies import CurrentUser, require_admin_not_support, require_roles
from app.crud import invitation as invitation_crud
from app.db.database import get_db
from app.models.church import Church
from app.models.invitation import Invitation
from app.schemas.auth import Password, normalise_email
from app.services.audit import record_audit
from app.services.email import EmailSender, get_email_sender, invitation_email

logger = logging.getLogger(__name__)
router = APIRouter()

Role = Literal["church_admin", "secretary", "finance", "group_leader", "member"]


class InvitationCreate(BaseModel):
    email: str
    role: Role
    branch_id: Optional[UUID] = None
    member_id: Optional[UUID] = None

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return normalise_email(value)


class InvitationAccept(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    password: Optional[Password] = None  # required only when the email has no account yet


def _serialize(row: Invitation) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "role": row.role,
        "branch_id": row.branch_id,
        "member_id": row.member_id,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "expired": row.expires_at <= datetime.now(timezone.utc),
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
    current_user: CurrentUser = Depends(require_admin_not_support),
):
    # Invitations send email from our domain with a church-chosen name: cap how many a church can send.
    if limiter.hit(f"invite|{current_user.church_id}", 30, 3600) is not None:
        raise HTTPException(status_code=429, detail="Too many invitations sent. Please try again later.")
    from app.services.plans import PlanLimitError, enforce_limit

    try:  # pending invitations will become users, so count them against the plan too
        pending = len(invitation_crud.list_pending(db, current_user.church_id))
        enforce_limit(db, current_user.church, "users", adding=pending + 1)
    except PlanLimitError as exc:
        raise HTTPException(status_code=402, detail={"code": "plan_limit", "limit": "users", "message": str(exc)})
    branch_id = payload.branch_id
    if current_user.is_branch_scoped:  # a branch admin can only bring people into their own branch
        if branch_id is None:
            branch_id = current_user.branch_id
        elif branch_id != current_user.branch_id:
            raise HTTPException(status_code=403, detail="You can only invite people into your own branch")
    if branch_id and not invitation_crud.branch_is_active_in_church(db, current_user.church_id, branch_id):
        raise HTTPException(status_code=400, detail="Branch not found in this church")
    if payload.member_id and not invitation_crud.member_exists_in_church(db, current_user.church_id, payload.member_id):
        raise HTTPException(status_code=400, detail="Member not found in this church")

    try:
        invitation, raw_token = invitation_crud.create_invitation(
            db,
            church_id=current_user.church_id,
            invited_by=current_user.id,
            email=payload.email,
            role=payload.role,
            branch_id=branch_id,
            member_id=payload.member_id,
            expires_hours=settings.INVITE_EXPIRE_HOURS,
        )
    except invitation_crud.AlreadyMember:
        raise HTTPException(status_code=409, detail="That person is already a member of this church")

    record_audit(
        db,
        church_id=current_user.church_id,
        user_id=current_user.id,
        action="created",
        table_name="invitations",
        record_id=invitation.id,
        new_value={"email": invitation.email, "role": invitation.role, "branch_id": str(branch_id) if branch_id else None},
    )
    db.commit()

    link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/accept-invite?token={raw_token}"
    email_sent = True
    try:
        sender.send(
            invitation_email(
                to=invitation.email,
                church_name=current_user.church.name,
                role=invitation.role,
                link=link,
                expires_hours=settings.INVITE_EXPIRE_HOURS,
            )
        )
    except Exception:
        # The invitation exists; the admin can re-invite to send a fresh email.
        logger.exception("Could not send invitation email")
        email_sent = False

    return {"status": "success", "data": {**_serialize(invitation), "email_sent": email_sent}}


@router.get("/")
def list_invitations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("church_admin")),
):
    rows = invitation_crud.list_pending(db, current_user.church_id, branch_id=current_user.branch_id)
    return {"status": "success", "data": [_serialize(row) for row in rows], "total": len(rows)}


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_not_support),
):
    row = invitation_crud.get_pending(db, current_user.church_id, invitation_id)
    if row is None or (current_user.is_branch_scoped and row.branch_id != current_user.branch_id):
        raise HTTPException(status_code=404, detail="Invitation not found")
    invitation_crud.revoke(db, row)
    record_audit(
        db,
        church_id=current_user.church_id,
        user_id=current_user.id,
        action="revoked",
        table_name="invitations",
        record_id=row.id,
        new_value={"email": row.email},
    )
    db.commit()


@router.post("/accept")
def accept_invitation(payload: InvitationAccept, db: Session = Depends(get_db)):
    """Public. Redeems the emailed token; the person then signs in normally (no session is issued here)."""
    try:
        invitation, created = invitation_crud.accept(db, payload.token, payload.password)
    except invitation_crud.InvitationInvalid:
        raise HTTPException(status_code=400, detail="This invitation is invalid or has expired")
    except invitation_crud.PasswordRequired:
        raise HTTPException(status_code=422, detail="Choose a password to create your account")
    except invitation_crud.ExistingAccountPasswordRequired:
        raise HTTPException(status_code=422, detail={
            "code": "existing_account",
            "message": "You already have an account with this email. Enter your current password to join.",
        })
    except invitation_crud.WrongPassword:
        raise HTTPException(status_code=400, detail="Incorrect password")

    church = db.query(Church).filter(Church.id == invitation.church_id).first()
    return {
        "status": "success",
        "data": {
            "email": invitation.email,
            "role": invitation.role,
            "church": {"id": church.id, "name": church.name, "slug": church.slug},
            "account_created": created,
        },
    }
