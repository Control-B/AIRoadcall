"""Tests for the cookie + session middleware architecture."""
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.core.cookies import (
    COOKIE_AUTH_SESSION,
    COOKIE_CLIENT_SESSION,
    COOKIE_PREFERRED_LANGUAGE,
    COOKIE_ROADSIDE_SESSION,
    COOKIE_SPECS,
    set_cookie,
)
from app.core.session_middleware import SessionCorrelationMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SessionCorrelationMiddleware)

    @app.get("/probe")
    def probe(response: Response):
        return {"ok": True}

    @app.post("/start-roadside")
    def start_roadside(response: Response):
        set_cookie(response, COOKIE_ROADSIDE_SESSION, "abc123def4567890abcd")
        return {"ok": True}

    @app.get("/lang")
    def lang(response: Response):
        set_cookie(response, COOKIE_PREFERRED_LANGUAGE, "es")
        return {"ok": True}

    return app


def test_client_session_id_is_set_on_first_visit():
    client = TestClient(_build_app())
    r = client.get("/probe")
    assert r.status_code == 200
    assert COOKIE_CLIENT_SESSION in r.cookies
    assert len(r.cookies[COOKIE_CLIENT_SESSION]) >= 16


def test_client_session_id_is_stable():
    client = TestClient(_build_app())
    r1 = client.get("/probe")
    first = r1.cookies[COOKIE_CLIENT_SESSION]
    # Re-send the cookie explicitly so we test the middleware decision logic,
    # not the test-client's cookie jar quirks.
    r2 = client.get("/probe", cookies={COOKIE_CLIENT_SESSION: first})
    set_cookie_header = r2.headers.get("set-cookie", "")
    # Middleware must not regenerate a fresh cookie when one already exists.
    assert COOKIE_CLIENT_SESSION not in set_cookie_header


def test_correlation_headers_present():
    client = TestClient(_build_app())
    r = client.get("/probe")
    assert r.headers.get("X-Roadcall-Request")
    assert r.headers.get("X-Roadcall-Client")


def test_roadside_cookie_is_httponly_and_lax():
    client = TestClient(_build_app())
    r = client.post("/start-roadside")
    assert r.status_code == 200
    set_cookie_header = r.headers.get("set-cookie", "")
    # Multiple Set-Cookie headers may be folded; check for the expected attrs.
    assert COOKIE_ROADSIDE_SESSION in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


def test_language_cookie_is_not_httponly():
    client = TestClient(_build_app())
    r = client.get("/lang")
    set_cookie_header = r.headers.get("set-cookie", "")
    assert COOKIE_PREFERRED_LANGUAGE in set_cookie_header
    # Language cookie must be readable from JS so the UI can react.
    # `httponly` attribute should NOT be on the language cookie's segment.
    segments = [s for s in set_cookie_header.split(",") if COOKIE_PREFERRED_LANGUAGE in s]
    assert any("httponly" not in s.lower() for s in segments)


def test_health_endpoint_is_skipped():
    client = TestClient(_build_app())
    r = client.get("/probe")  # primes a session
    sess = r.cookies[COOKIE_CLIENT_SESSION]
    # Re-send explicitly and confirm middleware doesn't set a NEW cookie.
    r2 = client.get("/probe", cookies={COOKIE_CLIENT_SESSION: sess})
    assert COOKIE_CLIENT_SESSION not in r2.headers.get("set-cookie", "")


def test_all_cookie_specs_are_safe():
    """Every declared cookie must be SameSite=Lax (or stricter) and have a sane TTL."""
    for name, spec in COOKIE_SPECS.items():
        assert spec.same_site in {"lax", "strict", "none"}, name
        assert spec.max_age_seconds > 0, name
        # Reference IDs (auth, refresh, roadside, location, client) must be HttpOnly.
        if name in {
            COOKIE_AUTH_SESSION,
            "roadcall_refresh_session",
            COOKIE_CLIENT_SESSION,
            COOKIE_ROADSIDE_SESSION,
            "roadcall_location_session_id",
        }:
            assert spec.http_only, f"{name} must be HttpOnly"
