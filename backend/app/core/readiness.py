"""Which third-party settings are still missing. Never returns secret values."""
from __future__ import annotations

from app.core.config import settings


def readiness_checks() -> list[dict]:
    """One entry per integration: ``ok`` plus a plain-language ``detail`` of what to set."""
    email_ok = settings.EMAIL_BACKEND.strip().lower() == "sendgrid" and bool(settings.SENDGRID_API_KEY)
    sms_ok = settings.SMS_PROVIDER.strip().lower() == "arkesel" and bool(settings.ARKESEL_API_KEY)
    billing = settings.BILLING_PROVIDER.strip().lower()
    billing_ok = billing == "seevplus" and bool(settings.SEEVPLUS_API_KEY and settings.BILLING_WEBHOOK_SECRET)
    cloudinary_ok = bool(settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET)
    return [
        {"key": "email", "ok": email_ok, "required": True,
         "detail": "Set EMAIL_BACKEND=sendgrid, SENDGRID_API_KEY and a verified FROM_EMAIL. Until then invitations "
                   "and password resets are only logged, never delivered."},
        {"key": "sms", "ok": sms_ok, "required": True,
         "detail": "Set SMS_PROVIDER=arkesel and ARKESEL_API_KEY (and register a sender ID per church)."},
        {"key": "billing", "ok": billing_ok, "required": False,
         "detail": f"BILLING_PROVIDER={billing}. For online payments set BILLING_PROVIDER=seevplus, SEEVPLUS_API_KEY "
                   "and BILLING_WEBHOOK_SECRET; 'manual' means an operator confirms payments by hand."},
        {"key": "storage", "ok": cloudinary_ok, "required": True,
         "detail": "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET (logo and photo uploads "
                   "cannot be saved on a serverless host without it)."},
        {"key": "cron", "ok": bool(settings.CRON_SECRET), "required": True,
         "detail": "Set CRON_SECRET so scheduled jobs (SMS reminders, purging closed churches) can run."},
        {"key": "rate_limit", "ok": settings.RATE_LIMIT_ENABLED and settings.RATE_LIMIT_BACKEND == "database",
         "required": True, "detail": "Keep RATE_LIMIT_ENABLED=true and RATE_LIMIT_BACKEND=database in production."},
        {"key": "cors", "ok": "localhost" not in settings.CORS_ORIGINS and "127.0.0.1" not in settings.CORS_ORIGINS,
         "required": True, "detail": "CORS_ORIGINS must list only your real frontend origin(s)."},
    ]


def production_warnings() -> list[str]:
    return [f"{c['key']}: {c['detail']}" for c in readiness_checks() if c["required"] and not c["ok"]]
