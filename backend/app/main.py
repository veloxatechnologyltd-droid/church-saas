import os
import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import attendance, audit, auth, communication, donations, events, families, groups, invitations, members, pastoral, reports
from app.core.config import settings
from app.db.database import check_database_connection

logger = logging.getLogger(__name__)

app = FastAPI(title="Living Spring CMS API", version="1.0.0")

os.makedirs("uploads/members", exist_ok=True)

_cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(invitations.router, prefix="/api/v1/invitations", tags=["Invitations"])
app.include_router(members.router, prefix="/api/v1/members", tags=["Members"])
app.include_router(families.router, prefix="/api/v1/families", tags=["Families"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(donations.router, prefix="/api/v1/donations", tags=["Finance"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groups"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(communication.router, prefix="/api/v1/communication", tags=["Communication"])
app.include_router(pastoral.router, prefix="/api/v1/pastoral", tags=["Pastoral Care"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


@app.get("/")
def root() -> dict:
    return {"status": "success", "data": {"message": "Living Spring CMS API is running"}}


@app.get("/health")
def health() -> dict:
    """Lightweight probe for Render / load balancers (no DB check)."""
    return {"status": "ok"}


@app.get("/health/db")
def database_health() -> dict:
    """Operational probe that verifies the configured database is reachable."""
    try:
        check_database_connection()
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
    return {"status": "ok", "database": "reachable"}
