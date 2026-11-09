from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# bcrypt only uses the first 72 bytes, so longer passwords add nothing but confusion.
Password = Annotated[str, Field(min_length=8, max_length=72)]


class LoginRequest(BaseModel):
    email: str
    password: str


class SwitchChurchRequest(BaseModel):
    church_id: UUID


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Password


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: Password


class ChurchAccess(BaseModel):
    """One church the user can sign in to, with their role there."""

    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    status: str
    plan: Optional[str] = None
    currency: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    onboarding_completed: bool = False
    role: str
    branch_id: Optional[UUID] = None


def normalise_email(value: str) -> str:
    value = value.strip().lower()
    local, _, domain = value.partition("@")
    if not local or "." not in domain or " " in value or value.count("@") != 1:
        raise ValueError("Enter a valid email address")
    return value


class EmailField(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return normalise_email(value)
