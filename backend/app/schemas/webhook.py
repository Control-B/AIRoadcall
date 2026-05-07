from pydantic import BaseModel
from typing import Optional, Any


class StripeWebhookEvent(BaseModel):
    """Minimal representation of a Stripe webhook event."""
    id: str
    type: str
    data: dict[str, Any]
