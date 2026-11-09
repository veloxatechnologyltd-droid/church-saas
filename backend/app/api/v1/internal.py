"""Scheduled jobs, triggered by the host's cron (Vercel Cron / Render cron / any scheduler).

Protected by ``CRON_SECRET``: the caller must send ``Authorization: Bearer <CRON_SECRET>``.
Disabled entirely when the secret is not configured.
"""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.communication import run_due_reminders
from app.db.database import get_db
from app.db.tenancy import clear_tenant

router = APIRouter()


def _require_cron(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.CRON_SECRET}"
    if not settings.CRON_SECRET or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/cron/reminders", dependencies=[Depends(_require_cron)])
@router.post("/cron/reminders", dependencies=[Depends(_require_cron)])
def cron_reminders(db: Session = Depends(get_db)):
    clear_tenant(db)
    results = run_due_reminders(db)
    return {"status": "success", "data": {"processed": len(results), "results": results}}
