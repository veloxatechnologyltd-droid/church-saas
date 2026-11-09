from datetime import date, datetime, time
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AttendanceSessionCreate(BaseModel):
    title: str
    session_date: date
    session_type: Optional[str] = None
    session_start_time: Optional[time] = None
    notes: Optional[str] = None


class AttendanceSessionResponse(BaseModel):
    id: UUID
    title: str
    session_date: date
    session_type: Optional[str] = None
    session_start_time: Optional[time] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    checkin_code: Optional[str] = None
    checkin_open: bool = False

    class Config:
        from_attributes = True


class AttendanceMarkItem(BaseModel):
    member_id: UUID
    status: Literal["present", "absent", "excused"]
    notes: Optional[str] = None


class AttendanceMarkRequest(BaseModel):
    records: list[AttendanceMarkItem] = Field(min_length=1)


class AttendanceRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    member_id: UUID
    status: str
    checked_in_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
