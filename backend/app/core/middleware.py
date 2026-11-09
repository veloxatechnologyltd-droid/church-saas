"""HTTP middleware: rate limiting for sensitive public endpoints and structured request logs.

The rate limiter is an in-process sliding window keyed by client IP + rule. With
several worker processes each one keeps its own window, so the effective limit is
``limit x workers``; that is acceptable for brute-force protection at this scale. Put a
shared store (Redis) behind ``RateLimiter`` before scaling out horizontally.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("app.request")

# (method, path prefix) -> (max requests, window seconds)
RATE_RULES: list[tuple[str, str, int, int]] = [
    ("POST", "/api/v1/auth/login", 10, 60),
    ("POST", "/api/v1/auth/forgot-password", 5, 300),
    ("POST", "/api/v1/auth/reset-password", 10, 300),
    ("POST", "/api/v1/invitations/accept", 10, 300),
    ("POST", "/api/v1/signup", 5, 3600),
    ("GET", "/api/v1/signup/slug-available", 60, 60),
    ("POST", "/api/v1/public/", 20, 300),
    ("GET", "/api/v1/public/", 120, 60),
]


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: int) -> int | None:
        """Record a hit; return seconds to wait if over the limit, else ``None``."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return int(window - (now - hits[0])) + 1
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    # Render/Vercel sit behind a proxy that sets X-Forwarded-For; the first entry is the client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.RATE_LIMIT_ENABLED:
            path = request.url.path
            for method, prefix, limit, window in RATE_RULES:
                if request.method == method and path.startswith(prefix):
                    wait = limiter.hit(f"{client_ip(request)}|{method}|{prefix}", limit, window)
                    if wait is not None:
                        return JSONResponse(
                            status_code=429,
                            content={"detail": "Too many attempts. Please wait a moment and try again."},
                            headers={"Retry-After": str(wait)},
                        )
                    break
        return await call_next(request)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """One log line per request with a request id, status, duration and church id."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error request_id=%s path=%s", request_id, request.url.path)
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        record = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "church_id": getattr(request.state, "church_id", None),
            "ip": client_ip(request),
        }
        if settings.LOG_JSON:
            logger.info(json.dumps(record))
        else:
            logger.info("%(method)s %(path)s %(status)s %(duration_ms)sms church=%(church_id)s rid=%(request_id)s", record)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
