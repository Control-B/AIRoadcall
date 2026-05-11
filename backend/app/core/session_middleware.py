"""Session correlation middleware.

For *every* HTTP request:
  1. Ensure a stable ``roadcall_client_session_id`` cookie (anonymous, 30d).
  2. Stash all known ``roadcall_*`` session IDs onto ``request.state`` so any
     downstream handler / log line can correlate them with ``user_id`` and
     ``job_id``.
  3. Echo the correlation IDs back as response headers (``X-Roadcall-Client``,
     ``X-Roadcall-Request``) so the frontend / browser dev-tools can debug.

Skips static / health endpoints to keep the hot path cheap.
"""
from __future__ import annotations

import secrets
import time
from typing import Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.cookies import (
    COOKIE_AI_CONVERSATION,
    COOKIE_AUTH_SESSION,
    COOKIE_CLIENT_SESSION,
    COOKIE_LOCATION_SESSION,
    COOKIE_ROADSIDE_SESSION,
    set_cookie,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_SKIP_PREFIXES: tuple[str, ...] = (
    "/health",
    "/api/health",
    "/api/webhooks/",   # signed webhooks shouldn't get session cookies
    "/static/",
    "/favicon",
)

_TRACKED_COOKIES: tuple[str, ...] = (
    COOKIE_CLIENT_SESSION,
    COOKIE_AUTH_SESSION,
    COOKIE_ROADSIDE_SESSION,
    COOKIE_LOCATION_SESSION,
    COOKIE_AI_CONVERSATION,
)


def _should_skip(path: str) -> bool:
    return any(path.startswith(p) for p in _SKIP_PREFIXES)


class SessionCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        skip = _should_skip(path)

        # Build the correlation snapshot up front so handlers can read it.
        client_id = request.cookies.get(COOKIE_CLIENT_SESSION)
        ids: dict[str, str | None] = {
            name: request.cookies.get(name) for name in _TRACKED_COOKIES
        }
        request.state.session_ids = ids
        request.state.client_session_id = client_id
        request.state.request_id = secrets.token_urlsafe(12)
        request.state.request_started_at = time.perf_counter()

        # Run the handler.
        response: Response = await call_next(request)

        # Set the anonymous client session if missing (skip on webhook/health).
        if not skip and not client_id:
            new_id = secrets.token_urlsafe(24)
            try:
                set_cookie(response, COOKIE_CLIENT_SESSION, new_id)
                request.state.client_session_id = new_id
            except Exception:  # pragma: no cover - cookie set should never fail
                logger.warning("Failed to set client session cookie")

        # Echo correlation headers for debugging.
        response.headers["X-Roadcall-Request"] = request.state.request_id
        if request.state.client_session_id:
            response.headers["X-Roadcall-Client"] = request.state.client_session_id

        # Structured trace (only when something interesting attached).
        if not skip:
            duration_ms = int((time.perf_counter() - request.state.request_started_at) * 1000)
            attached = {k: v for k, v in ids.items() if v}
            if attached or response.status_code >= 400:
                logger.info(
                    "request_complete",
                    extra={
                        "path": path,
                        "method": request.method,
                        "status": response.status_code,
                        "duration_ms": duration_ms,
                        "client_session_id": request.state.client_session_id,
                        "request_id": request.state.request_id,
                        "session_refs": _redact(attached),
                    },
                )

        return response


def _redact(ids: dict[str, str | None]) -> dict[str, str]:
    """Cookie *values* are opaque random IDs but we still truncate when logged."""
    out: dict[str, str] = {}
    for k, v in ids.items():
        if not v:
            continue
        out[k] = v[:8] + "…"
    return out


__all__ = ["SessionCorrelationMiddleware"]
