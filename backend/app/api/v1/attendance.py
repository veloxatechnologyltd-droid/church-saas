from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import GROUP_ROLES, PEOPLE_ROLES, get_current_user, require_roles
from app.crud import attendance as attendance_crud
from app.db.database import get_db
from app.core.config import settings
from app.schemas.outreach import CheckinToggle
from app.schemas.attendance import AttendanceMarkRequest, AttendanceRecordResponse, AttendanceSessionCreate, AttendanceSessionResponse
from app.services.audit import record_audit

router = APIRouter()


@router.get("/sessions")
def list_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GROUP_ROLES)),
):
    sessions, total = attendance_crud.list_sessions(db, skip=skip, limit=limit)
    data = [AttendanceSessionResponse.model_validate(s).model_dump() for s in sessions]
    page = (skip // limit) + 1
    return {"status": "success", "data": data, "total": total, "page": page, "limit": limit}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: AttendanceSessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    session = attendance_crud.create_session(db, payload, created_by=current_user.id)
    record_audit(db, user_id=current_user.id, action="created", table_name="attendance_sessions", record_id=session.id, new_value={"title": session.title, "session_date": session.session_date.isoformat()})
    db.commit()
    data = AttendanceSessionResponse.model_validate(session).model_dump()
    return {"status": "success", "data": data}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GROUP_ROLES)),
):
    session = attendance_crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    data = AttendanceSessionResponse.model_validate(session).model_dump()
    records = [AttendanceRecordResponse.model_validate(r).model_dump() for r in session.records]
    data["records"] = records
    return {"status": "success", "data": data}


@router.post("/sessions/{session_id}/mark")
def mark_attendance(
    session_id: UUID,
    payload: AttendanceMarkRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    session = attendance_crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    records = attendance_crud.mark_attendance(db, session_id, payload.records)
    record_audit(db, user_id=current_user.id, action="marked", table_name="attendance_records", record_id=session_id, new_value={"record_count": len(records)})
    db.commit()
    data = [AttendanceRecordResponse.model_validate(r).model_dump() for r in records]
    return {"status": "success", "data": data}


@router.post("/sessions/{session_id}/checkin")
def toggle_self_checkin(
    session_id: UUID,
    payload: CheckinToggle,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary", "group_leader")),
):
    """Open or close QR self check-in for a session. The code is kept when reopening."""
    session = attendance_crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    attendance_crud.set_self_checkin(db, session, payload.open)
    record_audit(db, user_id=current_user.id, action="checkin_opened" if payload.open else "checkin_closed",
                 table_name="attendance_sessions", record_id=session.id)
    db.commit()
    db.refresh(session)
    return {"status": "success", "data": _checkin_payload(session)}


def _checkin_payload(session) -> dict:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return {
        "checkin_code": session.checkin_code,
        "checkin_open": session.checkin_open,
        "checkin_url": f"{base}/checkin/{session.checkin_code}" if session.checkin_code else None,
    }


@router.get("/member/{member_id}")
def member_history(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*PEOPLE_ROLES)),
):
    from app.crud.member import get_member

    if not get_member(db, member_id):
        raise HTTPException(status_code=404, detail="Member not found")
    history, attendance_percentage = attendance_crud.member_attendance_history(db, member_id)
    return {
        "status": "success",
        "data": {
            "member_id": member_id,
            "attendance_percentage": attendance_percentage,
            "history": history,
        },
    }


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GROUP_ROLES)),
):
    stats = attendance_crud.attendance_summary(db)
    return {"status": "success", "data": stats}
