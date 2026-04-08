import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def generate_magic_link_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Hash a token for safe database storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_signed_token(job_id: str, public_job_id: str) -> str:
    """Create a JWT-signed magic link token embedding job reference."""
    raw_token = generate_magic_link_token()
    payload = {
        "sub": public_job_id,
        "jti": raw_token,
        "job_id": str(job_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.MAGIC_LINK_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    signed = jwt.encode(payload, settings.MAGIC_LINK_SECRET, algorithm=ALGORITHM)
    return signed


def decode_magic_link_token(token: str) -> dict | None:
    """Decode and validate a magic link JWT token. Returns claims or None."""
    try:
        payload = jwt.decode(token, settings.MAGIC_LINK_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_public_job_id() -> str:
    """Generate a short human-friendly public job ID."""
    return f"RC-{secrets.token_hex(4).upper()}"
