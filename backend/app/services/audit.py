from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    church_id: UUID | None = None,
    user_id: UUID | None,
    action: str,
    table_name: str,
    record_id: UUID | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an audit row. ``church_id`` defaults to the session's active church (see
    ``app.db.tenancy``); with neither, it fails loudly: the audit trail is tenant data."""
    if church_id is None:
        from app.db.tenancy import current_church_id

        church_id = current_church_id(db)
    if church_id is None:
        raise ValueError("record_audit needs a church: pass church_id or use a tenant-bound session")
    entry = AuditLog(
        church_id=church_id,
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)
    return entry
