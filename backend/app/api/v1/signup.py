"""Public self-service signup: a new church, its first admin, and a trial."""
from typing import Annotated, Optional

from app.core.config import settings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.v1.auth import session_payload
from app.core.security import verify_password
from app.crud import auth as auth_crud
from app.db.database import get_db
from app.schemas.auth import Password, normalise_email
from app.services.onboarding import create_church, slug_problem, slug_taken, slugify, suggest_slug

router = APIRouter()

Name = Annotated[str, Field(min_length=1, max_length=80)]


class SignupRequest(BaseModel):
    church_name: Annotated[str, Field(min_length=3, max_length=120)]
    slug: Optional[str] = Field(default=None, max_length=40)
    first_name: Name
    last_name: Name
    email: str
    password: Password
    phone: Optional[str] = Field(default=None, max_length=30)
    country: str = Field(default="GH", min_length=2, max_length=2)
    timezone: str = Field(default="Africa/Accra", max_length=64)
    currency: str = Field(default="GHS", min_length=3, max_length=3)
    denomination: Optional[str] = Field(default=None, max_length=80)
    # Spam trap: real users never see or fill this field.
    website: Optional[str] = None
    # Explicit consent to the Terms of Service and Privacy Policy (recorded with the church).
    accept_terms: bool = Field(default=False, validate_default=True)

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must accept the Terms of Service and Privacy Policy")
        return value

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalise_email(value)

    @field_validator("church_name", "first_name", "last_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value


@router.get("/slug-available")
def slug_available(slug: str = Query(..., max_length=80), db: Session = Depends(get_db)):
    cleaned = slugify(slug)
    problem = slug_problem(cleaned)
    available = problem is None and not slug_taken(db, cleaned)
    return {
        "status": "success",
        "data": {
            "slug": cleaned,
            "available": available,
            "reason": problem or (None if available else "That address is already taken"),
            "suggestion": cleaned if available else suggest_slug(db, cleaned or slug),
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if payload.website:
        raise HTTPException(status_code=400, detail="Signup could not be completed")

    slug = slugify(payload.slug or payload.church_name)
    if payload.slug:
        problem = slug_problem(slug)
        if problem:
            raise HTTPException(status_code=422, detail=f"Church address: {problem}")
        if slug_taken(db, slug):
            raise HTTPException(status_code=409, detail="That church address is already taken")
    else:
        slug = suggest_slug(db, slug)

    user = auth_crud.get_user_by_email(db, payload.email)
    if user is not None:
        # An existing person may start another church, but must prove it is them.
        if not verify_password(payload.password, user.hashed_password) or not user.is_active:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Sign in with your password, or reset it.",
            )
    else:
        from app.core.security import hash_password
        from app.models.user import User

        user = User(email=payload.email, hashed_password=hash_password(payload.password), is_active=True)
        db.add(user)
        db.flush()

    church, membership = create_church(
        db, name=payload.church_name, slug=slug, user=user, first_name=payload.first_name,
        last_name=payload.last_name, phone=payload.phone, country=payload.country.upper(),
        timezone_name=payload.timezone, currency=payload.currency.upper(), denomination=payload.denomination,
    )
    from datetime import datetime, timezone

    from app.services.audit import record_audit

    church.settings = {**(church.settings or {}), "terms_accepted": {
        "version": settings.LEGAL_VERSION, "at": datetime.now(timezone.utc).isoformat(), "by_user_id": str(user.id),
    }}
    record_audit(db, user_id=user.id, action="church_created", table_name="churches", record_id=church.id,
                 new_value={"name": church.name, "slug": church.slug})
    db.commit()
    db.refresh(church)
    db.refresh(membership)
    return {"status": "success", "data": session_payload(db, user, membership, church)}
