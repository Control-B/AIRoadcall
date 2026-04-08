"""LiveKit Cloud AI telephony integration service.

Handles:
- Outbound SIP calls to mechanics via LiveKit Cloud
- Room management for AI agent <-> mechanic calls
- Webhook signature verification
- Call status tracking

LiveKit Cloud Architecture:
  FastAPI creates a room + dispatches an AI agent → LiveKit connects
  the agent to the mechanic via SIP trunk → mechanic answers →
  AI agent determines availability → webhook fires back to FastAPI
"""
import hashlib
import hmac
import base64
import json
import time
import uuid
from typing import Optional

import httpx
from livekit.api import LiveKitAPI, SIPTrunkInfo

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LiveKitService:
    """LiveKit Cloud telephony integration for mechanic dispatch calls."""

    @staticmethod
    def _get_api() -> LiveKitAPI:
        """Create an authenticated LiveKit API client."""
        return LiveKitAPI(
            url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )

    @staticmethod
    def verify_webhook_signature(body: bytes, auth_header: str) -> bool:
        """Verify LiveKit webhook signature using HMAC-SHA256.

        LiveKit signs webhook payloads with the API secret.
        The Authorization header contains: Bearer <token>
        We verify by decoding the JWT with the API secret.

        Args:
            body: Raw request body bytes
            auth_header: The Authorization header value

        Returns:
            True if the signature is valid
        """
        if not settings.LIVEKIT_API_SECRET:
            logger.warning("LIVEKIT_API_SECRET not configured, skipping verification")
            return True

        try:
            from jose import jwt

            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            else:
                token = auth_header

            # LiveKit webhook tokens are JWTs signed with the API secret
            decoded = jwt.decode(
                token,
                settings.LIVEKIT_API_SECRET,
                algorithms=["HS256"],
            )

            # Verify the body hash matches
            body_hash = hashlib.sha256(body).hexdigest()
            if decoded.get("sha256") != body_hash:
                logger.warning("LiveKit webhook body hash mismatch")
                return False

            return True

        except Exception as e:
            logger.warning(f"LiveKit webhook signature verification failed: {e}")
            return False

    @staticmethod
    async def initiate_mechanic_call(
        mechanic_phone: str,
        mechanic_name: str,
        job_summary: str,
        job_id: str,
        dispatch_attempt_id: str,
    ) -> dict:
        """Initiate an outbound SIP call to a mechanic via LiveKit Cloud.

        Flow:
        1. Create a LiveKit room for this dispatch attempt
        2. Create a SIP participant (outbound call) in that room
        3. The AI agent (configured in LiveKit Cloud) auto-joins and speaks
        4. When the call ends, LiveKit fires a webhook to /webhooks/livekit

        Args:
            mechanic_phone: Mechanic's phone number (E.164 format)
            mechanic_name: Name for context
            job_summary: Issue description for the AI agent prompt
            job_id: Internal job UUID
            dispatch_attempt_id: Dispatch attempt UUID

        Returns:
            Dict with room_name and sip_call_id
        """
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            logger.info(
                f"[STUB] Would call mechanic {mechanic_name} at {mechanic_phone} "
                f"for job {job_id} (LiveKit not configured)"
            )
            return {
                "status": "stub",
                "message": "Call not initiated — LiveKit keys not configured",
                "room_name": f"dispatch-{dispatch_attempt_id}",
            }

        room_name = f"dispatch-{dispatch_attempt_id}"

        try:
            api = LiveKitService._get_api()

            # 1. Create a room for the call
            room = await api.room.create_room(
                name=room_name,
                metadata=json.dumps({
                    "type": "mechanic_dispatch",
                    "job_id": job_id,
                    "dispatch_attempt_id": dispatch_attempt_id,
                    "mechanic_name": mechanic_name,
                    "mechanic_phone": mechanic_phone,
                    "job_summary": job_summary,
                }),
                # Auto-close room after 5 minutes (call timeout)
                empty_timeout=300,
                max_participants=3,  # AI agent + SIP participant + optional monitor
            )

            logger.info(f"Created LiveKit room: {room_name} for dispatch {dispatch_attempt_id}")

            # 2. Create outbound SIP call to the mechanic
            sip_participant = await api.sip.create_sip_participant(
                room_name=room_name,
                sip_trunk_id=settings.LIVEKIT_SIP_TRUNK_ID,
                sip_call_to=mechanic_phone,
                participant_identity=f"mechanic-{dispatch_attempt_id}",
                participant_name=mechanic_name,
                participant_metadata=json.dumps({
                    "role": "mechanic",
                    "job_id": job_id,
                    "dispatch_attempt_id": dispatch_attempt_id,
                }),
            )

            logger.info(
                f"Initiated SIP call to {mechanic_phone} in room {room_name}, "
                f"participant: {sip_participant.participant_id if hasattr(sip_participant, 'participant_id') else 'unknown'}"
            )

            return {
                "status": "calling",
                "room_name": room_name,
                "sip_call_id": getattr(sip_participant, "sip_call_id", None),
                "participant_id": getattr(sip_participant, "participant_id", None),
            }

        except Exception as e:
            logger.error(f"Failed to initiate LiveKit call to {mechanic_phone}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "room_name": room_name,
            }

    @staticmethod
    async def end_room(room_name: str) -> bool:
        """Force-close a LiveKit room (e.g., when a mechanic is assigned elsewhere).

        Args:
            room_name: The room to close

        Returns:
            True if the room was successfully closed
        """
        if not settings.LIVEKIT_API_KEY:
            return True

        try:
            api = LiveKitService._get_api()
            await api.room.delete_room(room_name)
            logger.info(f"Closed LiveKit room: {room_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to close LiveKit room {room_name}: {e}")
            return False

    @staticmethod
    async def cancel_dispatch_calls(job_id: str, except_room: str | None = None) -> int:
        """Cancel all active dispatch call rooms for a job.

        Called when a mechanic accepts — stop calling others.

        Args:
            job_id: Job UUID to cancel calls for
            except_room: Room name to keep alive (the accepted call)

        Returns:
            Number of rooms closed
        """
        if not settings.LIVEKIT_API_KEY:
            return 0

        try:
            api = LiveKitService._get_api()
            rooms = await api.room.list_rooms()
            closed = 0

            for room in rooms:
                if room.name == except_room:
                    continue

                try:
                    metadata = json.loads(room.metadata or "{}")
                    if metadata.get("job_id") == job_id and metadata.get("type") == "mechanic_dispatch":
                        await api.room.delete_room(room.name)
                        closed += 1
                        logger.info(f"Cancelled dispatch room: {room.name}")
                except (json.JSONDecodeError, Exception):
                    continue

            return closed
        except Exception as e:
            logger.error(f"Failed to cancel dispatch calls for job {job_id}: {e}")
            return 0
