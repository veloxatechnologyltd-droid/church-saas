from datetime import date, datetime, time
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


AudienceType = Literal[
    "all_members",
    "active_members",
    "inactive_members",
    "department",
    "selected_members",
]
ReminderAudienceType = Literal["all_members", "active_members", "inactive_members", "department"]


class SMSCreate(BaseModel):
    message: str = Field(min_length=1, max_length=918)
    audience_type: AudienceType = "all_members"
    group_id: Optional[UUID] = None
    member_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_audience(self):
        if self.audience_type == "department" and not self.group_id:
            raise ValueError("group_id is required for a department audience")
        if self.audience_type == "selected_members" and not self.member_ids:
            raise ValueError("member_ids is required for a selected members audience")
        return self


class ReminderScheduleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    message_template: str = Field(min_length=1, max_length=918)
    frequency: Literal["weekly"] = "weekly"
    weekday: int = Field(ge=0, le=6)
    send_time: time
    timezone: str = "Africa/Accra"
    audience_type: ReminderAudienceType = "all_members"
    group_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.audience_type == "department" and not self.group_id:
            raise ValueError("group_id is required for a department audience")
        if self.audience_type != "department" and self.group_id:
            raise ValueError("group_id is only valid for a department audience")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ReminderScheduleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    message_template: Optional[str] = Field(default=None, min_length=1, max_length=918)
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    send_time: Optional[time] = None
    timezone: Optional[str] = None
    audience_type: Optional[ReminderAudienceType] = None
    group_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class ReminderScheduleResponse(BaseModel):
    id: UUID
    name: str
    message_template: str
    frequency: str
    weekday: int
    send_time: time
    timezone: str
    audience_type: str
    group_id: Optional[UUID] = None
    group_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CommunicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    subject: Optional[str] = None
    body: str
    audience_type: Optional[str] = None
    group_id: Optional[UUID] = None
    recipient_count: int
    successful_count: int
    failed_count: int
    provider_message_id: Optional[str] = None
    credits_used: Optional[int] = None
    sent_by: Optional[UUID] = None
    sent_at: datetime
    status: str
