"""Admin authentication — login endpoint and JWT session tokens."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.cookies import (
    COOKIE_AUTH_SESSION,
    clear_cookie,
    read_cookie,
    set_cookie,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/admin", tags=["admin-auth"])

# ── Simple token store (in-memory, resets on restart) ────
# For a single-admin SaaS dashboard this is fine.
# Tokens are opaque random strings, not JWTs — simpler and no secret key needed.
_active_tokens: dict[str, dict] = {}
TOKEN_EXPIRY_HOURS = 24


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_at: str
    username: str


class AuthStatus(BaseModel):
    authenticated: bool
    username: str


# ── Login ────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def admin_login(data: LoginRequest, response: Response):
    """Authenticate admin and return a session token.

    The same opaque token is *also* set as an HttpOnly+Secure cookie
    (``roadcall_auth_session``) so that we can move away from localStorage
    without breaking existing dashboards.
    """
    username = data.username.strip()
    password = data.password.strip()
    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        logger.warning(f"Failed admin login attempt: {data.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Generate token
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

    _active_tokens[token] = {
        "username": username,
        "expires_at": expires_at,
    }

    # Clean up expired tokens
    now = datetime.now(timezone.utc)
    expired = [t for t, v in _active_tokens.items() if v["expires_at"] < now]
    for t in expired:
        del _active_tokens[t]

    # Set HttpOnly cookie alongside the JSON token (defense-in-depth migration).
    set_cookie(response, COOKIE_AUTH_SESSION, token)

    logger.info(f"Admin login successful: {username}")

    return LoginResponse(
        token=token,
        expires_at=expires_at.isoformat(),
        username=username,
    )


@router.get("/auth-status", response_model=AuthStatus)
async def check_auth(request: Request, x_admin_key: str = Header(default="")):
    """Check if a token is valid (header *or* cookie)."""
    token = x_admin_key or read_cookie(request, COOKIE_AUTH_SESSION) or ""
    session = _active_tokens.get(token)
    if not session:
        # Also accept the static ADMIN_API_KEY for backward compat
        if token and token == settings.ADMIN_API_KEY:
            return AuthStatus(authenticated=True, username=settings.ADMIN_USERNAME)
        return AuthStatus(authenticated=False, username="")

    if session["expires_at"] < datetime.now(timezone.utc):
        del _active_tokens[token]
        return AuthStatus(authenticated=False, username="")

    return AuthStatus(authenticated=True, username=session["username"])


@router.post("/logout")
async def admin_logout(
    request: Request,
    response: Response,
    x_admin_key: str = Header(default=""),
):
    """Invalidate a session token (header or cookie) and clear the cookie."""
    token = x_admin_key or read_cookie(request, COOKIE_AUTH_SESSION) or ""
    if token in _active_tokens:
        del _active_tokens[token]
    clear_cookie(response, COOKIE_AUTH_SESSION)
    return {"success": True}


# ── Dependency for protected routes ──────────────────────

async def verify_admin(
    request: Request,
    x_admin_key: str = Header(default=""),
):
    """Verify admin token (header *or* HttpOnly cookie) or static API key."""
    token = x_admin_key or read_cookie(request, COOKIE_AUTH_SESSION) or ""

    # Check session tokens first
    session = _active_tokens.get(token)
    if session:
        if session["expires_at"] >= datetime.now(timezone.utc):
            return session["username"]
        else:
            del _active_tokens[token]

    # Fall back to static API key (used by ops scripts).
    if token and token == settings.ADMIN_API_KEY:
        return settings.ADMIN_USERNAME

    raise HTTPException(status_code=401, detail="Not authenticated")
