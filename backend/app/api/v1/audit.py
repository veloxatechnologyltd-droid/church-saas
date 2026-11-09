from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.audit import AuditLog

router = APIRouter()


@router.get("/")
def list_audit_logs(
    table_name: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    query = db.query(AuditLog)
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return {
        "status": "success",
        "data": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "action": row.action,
                "table_name": row.table_name,
                "record_id": row.record_id,
                "old_value": row.old_value,
                "new_value": row.new_value,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "total": len(rows),
    }
