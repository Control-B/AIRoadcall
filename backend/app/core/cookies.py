"""
Roadcall.ai cookie architecture.

Centralizes every cookie name, expiration, and security flag so that the
roadside, dispatch, AI-chat, and dashboard flows behave consistently across
the public site, mechanic dashboard, fleet portal, and admin tools.

Design rules (see docs/cookie-architecture.md):

  * Essential cookies only — no ad-tech or retargeting by default.
  * HttpOnly + SameSite=Lax for any cookie that grants access (auth/refresh).
  * Opaque random IDs only — never store GPS, payment, PII, or transcripts
    in the cookie itself. The cookie is *only* a reference into the database.
  * Short operational lifetime for in-flight roadside / GPS / AI sessions.
  * Long lifetime for harmless preferences (language, theme, consent choice).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Optional

from fastapi import Request, Response

from app.core.config import get_settings

# ── Cookie names ───────────────────────────────────────────────────────────────
# Keep these exact strings stable — frontend, middleware, and analytics all key
# on them. Add new names rather than renaming.

COOKIE_AUTH_SESSION         = "roadcall_auth_session"
COOKIE_REFRESH_SESSION      = "roadcall_refresh_session"
COOKIE_CLIENT_SESSION       = "roadcall_client_session_id"
COOKIE_ROADSIDE_SESSION     = "roadcall_roadside_session_id"
COOKIE_LOCATION_SESSION     = "roadcall_location_session_id"
COOKIE_AI_CONVERSATION      = "roadcall_ai_conversation_id"
COOKIE_PREFERRED_LANGUAGE   = "roadcall_preferred_language"
COOKIE_COOKIE_CONSENT       = "roadcall_cookie_consent"
COOKIE_ANALYTICS_CONSENT    = "roadcall_analytics_consent"


# ── Spec table ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CookieSpec:
    name: str
    max_age_seconds: int
    http_only: bool
    same_site: str = "lax"      # "lax" | "strict" | "none"
    path: str = "/"
    description: str = ""


_HOUR = 3600
_DAY = 24 * _HOUR

# Per-cookie policy. Keep small and explicit — anything outside this table is
# rejected by ``set_cookie`` to prevent ad-hoc cookies sneaking in.
COOKIE_SPECS: dict[str, CookieSpec] = {
    COOKIE_AUTH_SESSION: CookieSpec(
        name=COOKIE_AUTH_SESSION,
        max_age_seconds=24 * _HOUR,
        http_only=True,
        same_site="lax",
        description="Logged-in dashboard session token (opaque random).",
    ),
    COOKIE_REFRESH_SESSION: CookieSpec(
        name=COOKIE_REFRESH_SESSION,
        max_age_seconds=30 * _DAY,
        http_only=True,
        same_site="lax",
        path="/api/admin",      # only sent to refresh endpoints
        description="Long-lived refresh token. Restricted path.",
    ),
    COOKIE_CLIENT_SESSION: CookieSpec(
        name=COOKIE_CLIENT_SESSION,
        max_age_seconds=30 * _DAY,
        http_only=True,
        same_site="lax",
        description="Anonymous correlation ID for rate-limit & log tracing.",
    ),
    COOKIE_ROADSIDE_SESSION: CookieSpec(
        name=COOKIE_ROADSIDE_SESSION,
        max_age_seconds=6 * _HOUR,
        http_only=True,
        same_site="lax",
        description="Active roadside request reference. 6h operational window.",
    ),
    COOKIE_LOCATION_SESSION: CookieSpec(
        name=COOKIE_LOCATION_SESSION,
        max_age_seconds=60 * 60,    # 60 min
        http_only=True,
        same_site="lax",
        path="/locate",
        description="Short-lived GPS capture session (SMS link).",
    ),
    COOKIE_AI_CONVERSATION: CookieSpec(
        name=COOKIE_AI_CONVERSATION,
        max_age_seconds=24 * _HOUR,
        http_only=False,            # frontend AI chat reads it directly
        same_site="lax",
        description="AI chat conversation reference. 24h for anonymous users.",
    ),
    COOKIE_PREFERRED_LANGUAGE: CookieSpec(
        name=COOKIE_PREFERRED_LANGUAGE,
        max_age_seconds=180 * _DAY,
        http_only=False,
        same_site="lax",
        description="Preferred UI language (BCP-47).",
    ),
    COOKIE_COOKIE_CONSENT: CookieSpec(
        name=COOKIE_COOKIE_CONSENT,
        max_age_seconds=365 * _DAY,
        http_only=False,
        same_site="lax",
        description="Has the user dismissed/answered the consent banner.",
    ),
    COOKIE_ANALYTICS_CONSENT: CookieSpec(
        name=COOKIE_ANALYTICS_CONSENT,
        max_age_seconds=365 * _DAY,
        http_only=False,
        same_site="lax",
        description="Granted analytics cookies? 'granted' | 'denied'.",
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_production() -> bool:
    """Force Secure cookies anywhere except localhost dev."""
    settings = get_settings()
    base = (settings.APP_BASE_URL or settings.FRONTEND_URL or "").lower()
    return not ("localhost" in base or "127.0.0.1" in base)


def set_cookie(response: Response, name: str, value: str) -> None:
    """Set a cookie using its declared spec. Raises if the name is unknown.

    Forces ``Secure=True`` outside of local development so we never accidentally
    leak session tokens over HTTP.
    """
    spec = COOKIE_SPECS.get(name)
    if not spec:
        raise ValueError(f"Unknown cookie name '{name}'. Add a CookieSpec first.")
    response.set_cookie(
        key=spec.name,
        value=value,
        max_age=spec.max_age_seconds,
        path=spec.path,
        secure=_is_production(),
        httponly=spec.http_only,
        samesite=spec.same_site,
    )


def clear_cookie(response: Response, name: str) -> None:
    spec = COOKIE_SPECS.get(name)
    if not spec:
        return
    response.delete_cookie(key=spec.name, path=spec.path)


def read_cookie(request: Request, name: str) -> Optional[str]:
    return request.cookies.get(name)


def new_opaque_id(num_bytes: int = 24) -> str:
    """Cryptographically random URL-safe ID for any session reference."""
    return secrets.token_urlsafe(num_bytes)


def get_or_create_client_session_id(request: Request, response: Response) -> str:
    """Return the anonymous correlation ID, creating it if missing."""
    existing = read_cookie(request, COOKIE_CLIENT_SESSION)
    if existing and 16 <= len(existing) <= 96:
        return existing
    new_id = new_opaque_id()
    set_cookie(response, COOKIE_CLIENT_SESSION, new_id)
    return new_id


__all__ = [
    "COOKIE_AUTH_SESSION",
    "COOKIE_REFRESH_SESSION",
    "COOKIE_CLIENT_SESSION",
    "COOKIE_ROADSIDE_SESSION",
    "COOKIE_LOCATION_SESSION",
    "COOKIE_AI_CONVERSATION",
    "COOKIE_PREFERRED_LANGUAGE",
    "COOKIE_COOKIE_CONSENT",
    "COOKIE_ANALYTICS_CONSENT",
    "COOKIE_SPECS",
    "CookieSpec",
    "set_cookie",
    "clear_cookie",
    "read_cookie",
    "new_opaque_id",
    "get_or_create_client_session_id",
]
