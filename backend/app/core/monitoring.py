"""Optional Sentry error monitoring. Inactive unless ``SENTRY_DSN`` is set.

Privacy first: church records are sensitive, so no request bodies, cookies, auth headers,
query strings or user details are ever sent (``send_default_pii=False`` plus ``_scrub``).
Events carry only technical context: the exception, the route, ``church_id`` and
``request_id`` tags (opaque ids), the environment and the release.
"""
from __future__ import annotations

import logging
import os

from app.core.config import settings

logger = logging.getLogger("app.monitoring")
_enabled = False

_DROP_REQUEST_KEYS = ("data", "cookies", "query_string", "env")
_SAFE_HEADERS = {"user-agent", "content-type", "x-request-id"}


def _scrub(event: dict, hint: dict) -> dict:
    request = event.get("request")
    if isinstance(request, dict):
        for key in _DROP_REQUEST_KEYS:
            request.pop(key, None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {k: v for k, v in headers.items() if k.lower() in _SAFE_HEADERS}
    event.pop("user", None)
    return event


def init_monitoring() -> bool:
    """Start Sentry if configured. Never raises: monitoring must not stop the API booting."""
    global _enabled
    if not settings.SENTRY_DSN:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=os.getenv("VERCEL_GIT_COMMIT_SHA") or None,
            send_default_pii=False,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            before_send=_scrub,
        )
        _enabled = True
        logger.info("Sentry error monitoring enabled")
    except Exception:
        logger.exception("Could not start Sentry; continuing without it")
    return _enabled


def is_enabled() -> bool:
    return _enabled


def tag(**tags: str) -> None:
    """Attach opaque ids (church_id, request_id) to events from the current request."""
    if not _enabled:
        return
    try:
        import sentry_sdk

        for key, value in tags.items():
            if value is not None:
                sentry_sdk.set_tag(key, str(value))
    except Exception:  # pragma: no cover - never let tagging break a request
        pass
