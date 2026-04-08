from app.core.security import decode_magic_link_token
from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenService:
    """Centralized token validation logic."""

    @staticmethod
    def validate_token(token: str) -> dict | None:
        """Validate a magic-link JWT token. Returns claims or None."""
        claims = decode_magic_link_token(token)
        if not claims:
            logger.warning("Invalid magic link token attempted")
            return None
        return claims
