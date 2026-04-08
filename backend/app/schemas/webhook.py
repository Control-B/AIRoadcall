from pydantic import BaseModel
from typing import Optional, Any


class StripeWebhookEvent(BaseModel):
    """Minimal representation of a Stripe webhook event."""
    id: str
    type: str
    data: dict[str, Any]


class LiveKitWebhookEvent(BaseModel):
    """Representation of a LiveKit Cloud webhook event.

    LiveKit sends webhook events for room, participant, track, SIP,
    and agent-related activities.
    """
    event: str  # e.g. "room_started", "participant_joined", "sip_call_ended"
    room: Optional[dict[str, Any]] = None
    participant: Optional[dict[str, Any]] = None
    track: Optional[dict[str, Any]] = None
    id: Optional[str] = None
    created_at: Optional[int] = None
