from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


PastoralPriority = Literal["low", "normal", "high", "urgent"]
PastoralSource = Literal["manual", "attendance"]


class PastoralLogCreate(BaseModel):
    member_id: UUID
    log_type: str = Field(min_length=2, max_length=60)
    notes: str = Field(min_length=1, max_length=5000)
    status: str = Field(default="open", pattern="^(open|completed)$")
    priority: PastoralPriority = "normal"
    source: PastoralSource = "manual"
    follow_up_date: Optional[date] = None
    assigned_to: Optional[UUID] = None
    log_date: date


class PastoralLogUpdate(BaseModel):
    log_type: Optional[str] = Field(default=None, min_length=2, max_length=60)
    notes: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    status: Optional[str] = Field(default=None, pattern="^(open|completed)$")
    priority: Optional[PastoralPriority] = None
    follow_up_date: Optional[date] = None
    assigned_to: Optional[UUID] = None


class PastoralLogResponse(BaseModel):
    id: UUID
    member_id: UUID
    member_name: Optional[str] = None
    member_status: Optional[str] = None
    member_phone: Optional[str] = None
    log_type: str
    notes: str
    status: str
    priority: PastoralPriority
    source: PastoralSource
    follow_up_date: Optional[date] = None
    due_state: str
    assigned_to: Optional[UUID] = None
    assignee_name: Optional[str] = None
    logged_by: Optional[UUID] = None
    log_date: date
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
