import os
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import attendance, audit, auth, communication, donations, events, families, groups, invitations, members, pastoral, reports
from app.api.v1 import pledges, prayer_requests, public, visitors
from app.api.v1 import billing, branches, church, internal, platform, signup, team
from app.core.middleware import RateLimitMiddleware, RequestLogMiddleware, SecurityHeadersMiddleware
from app.db.tenancy import TenantViolation
from app.services.billing import BillingProviderError
from app.core.config import settings
from app.core.readiness import production_warnings
from app.db.database import check_database_connection

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title=f"{settings.PRODUCT_NAME} API",
    version="2.0.0",
    description="Multi-tenant church management API.",
    # Interactive docs are handy in development; production keeps the schema private.
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None,
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)

# Local uploads (dev only; production uses Cloudinary). Serverless hosts have a
# read-only filesystem, so failing to create the folder must not stop the app.
try:
    os.makedirs("uploads", exist_ok=True)
    _uploads_available = True
except OSError:
    _uploads_available = False

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY in ("change-this-secret", "change-this-to-a-long-random-secret"):
    raise RuntimeError("SECRET_KEY must be set to a long random value in production")
if settings.ENVIRONMENT == "production" and settings.BILLING_PROVIDER == "fake":
    raise RuntimeError("BILLING_PROVIDER=fake lets anyone mark invoices paid; use 'manual' (or a real provider) in production")

if settings.ENVIRONMENT == "production":
    # Not fatal (the app must boot while integrations are being set up), but never silent.
    for _warning in production_warnings():
        logging.getLogger("app.readiness").warning("NOT READY FOR PRODUCTION - %s", _warning)

_cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

# Order: the last added runs first. CORS must wrap everything (incl. 429 responses).
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _uploads_available:
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
app.include_router(visitors.router, prefix="/api/v1/visitors", tags=["Visitors"])
app.include_router(prayer_requests.router, prefix="/api/v1/prayer-requests", tags=["Prayer Requests"])
app.include_router(pledges.router, prefix="/api/v1/pledges", tags=["Pledges"])
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
app.include_router(signup.router, prefix="/api/v1/signup", tags=["Signup"])
app.include_router(church.router, prefix="/api/v1/church", tags=["Church settings"])
app.include_router(branches.router, prefix="/api/v1/branches", tags=["Branches"])
app.include_router(team.router, prefix="/api/v1/team", tags=["Team"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(billing.sms_router, prefix="/api/v1/sms-credits", tags=["SMS credits"])
app.include_router(platform.router, prefix="/api/v1/platform", tags=["Platform admin"])
app.include_router(internal.router, prefix="/api/v1/internal", tags=["Internal"], include_in_schema=False)


@app.exception_handler(TenantViolation)
async def _tenant_violation(request: Request, exc: TenantViolation):
    # Never reveal that the other church's record exists.
    logging.getLogger("app.security").warning("Tenant violation blocked: %s path=%s", exc, request.url.path)
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(BillingProviderError)
async def _billing_provider_error(request: Request, exc: BillingProviderError):
    # The payment provider failed or refused; nothing was charged and the invoice was rolled back.
    logging.getLogger("app.billing").error("Billing provider error: %s path=%s", exc, request.url.path)
    return JSONResponse(status_code=502, content={"detail": "The payment provider is unavailable. Please try again shortly."})


@app.get("/")
def root() -> dict:
    return {"status": "success", "data": {"message": f"{settings.PRODUCT_NAME} API is running"}}


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
