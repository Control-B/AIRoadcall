"""DO AI Gradient text chat service for shop telephony customers.

Provides text-based customer service using DigitalOcean's AI platform.
Each shop can have a customized text agent that handles SMS/web chat
conversations with the same context as their voice agent.
"""
import json
import uuid
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# In-memory conversation store (use Redis in production)
_conversations: dict[str, list[dict]] = {}


class DOAIChatService:
    """DigitalOcean AI Gradient chat service for shop text conversations."""

    @staticmethod
    async def chat(
        shop_config: dict,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> dict:
        """Send a message to the DO AI Gradient chat endpoint.

        Args:
            shop_config: The shop's agent configuration (prompt, context, etc.)
            message: The user's message
            conversation_id: Optional conversation ID for multi-turn

        Returns:
            Dict with reply, conversation_id, intent, is_qualified_lead
        """
        # Get or create conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        if conversation_id not in _conversations:
            _conversations[conversation_id] = []

        history = _conversations[conversation_id]

        # Build the system prompt from shop config
        system_prompt = _build_text_system_prompt(shop_config)

        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            reply = await _call_do_ai(messages, shop_config)

            # Store in conversation history
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": reply})
            _conversations[conversation_id] = history

            # Analyze intent and lead quality
            intent = _detect_intent(message)
            is_lead = _is_qualified_lead(history)
            actions = _suggest_actions(intent, history)

            return {
                "reply": reply,
                "conversation_id": conversation_id,
                "intent": intent,
                "is_qualified_lead": is_lead,
                "suggested_actions": actions,
            }

        except Exception as e:
            logger.error(f"DO AI chat error: {e}")
            return {
                "reply": (
                    f"I'm sorry, I'm having trouble right now. "
                    f"Please call us at {shop_config.get('fallback_phone', 'our main number')} "
                    f"for immediate assistance."
                ),
                "conversation_id": conversation_id,
                "intent": None,
                "is_qualified_lead": False,
                "suggested_actions": ["call_shop"],
            }


async def _call_do_ai(messages: list[dict], shop_config: dict) -> str:
    """Call the DigitalOcean AI Gradient chat completion API.

    DO AI Gradient uses an OpenAI-compatible API endpoint.
    """
    api_url = settings.DO_AI_ENDPOINT
    api_key = settings.DO_AI_API_KEY
    model = settings.DO_AI_MODEL

    if not api_url or not api_key:
        logger.warning("DO AI not configured, using fallback response")
        return _fallback_response(messages[-1]["content"], shop_config)

    # Use the shop's specific agent ID if configured
    agent_model = shop_config.get("text_agent_id") or model

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": agent_model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _fallback_response(message: str, shop_config: dict) -> str:
    """Generate a basic response when DO AI is not available."""
    business_name = shop_config.get("business_name", "our shop")
    return (
        f"Thank you for reaching out to {business_name}! "
        f"We've received your message and will get back to you shortly. "
        f"For immediate assistance, please call us."
    )


def _build_text_system_prompt(shop_config: dict) -> str:
    """Build a text-optimized system prompt from shop config."""
    base_prompt = shop_config.get("agent_prompt", "")

    text_addendum = """

ADDITIONAL INSTRUCTIONS FOR TEXT CHAT:
- Keep responses concise (2-3 sentences max)
- Use clear, simple language
- Include relevant details like pricing ranges when asked
- Offer to schedule a callback or appointment
- If the issue is urgent, recommend calling the shop directly
- Always try to capture: name, phone, vehicle info, what they need
- Format any lists or options clearly
- End messages with a clear next step or question"""

    return base_prompt + text_addendum


def _detect_intent(message: str) -> Optional[str]:
    """Simple intent detection from message text."""
    lower = message.lower()

    if any(w in lower for w in ("emergency", "roadside", "breakdown", "stuck", "stranded")):
        return "emergency"
    if any(w in lower for w in ("price", "cost", "how much", "quote", "estimate")):
        return "price_inquiry"
    if any(w in lower for w in ("appointment", "schedule", "book", "when can")):
        return "scheduling"
    if any(w in lower for w in ("repair", "fix", "broken", "service", "maintenance")):
        return "repair_request"
    if any(w in lower for w in ("tow", "towing", "haul")):
        return "tow_request"
    if any(w in lower for w in ("hours", "open", "close", "location", "where")):
        return "general_question"

    return "general_question"


def _is_qualified_lead(history: list[dict]) -> bool:
    """Determine if the conversation represents a qualified lead."""
    user_messages = " ".join(
        m["content"].lower() for m in history if m["role"] == "user"
    )

    signals = 0
    if any(w in user_messages for w in ("need", "looking for", "want", "require")):
        signals += 1
    if any(w in user_messages for w in ("truck", "semi", "diesel", "vehicle", "fleet")):
        signals += 1
    if any(w in user_messages for w in ("today", "tomorrow", "asap", "soon", "urgent")):
        signals += 1
    if any(w in user_messages for w in ("schedule", "appointment", "book", "come in")):
        signals += 1

    return signals >= 2


def _suggest_actions(intent: Optional[str], history: list[dict]) -> list[str]:
    """Suggest follow-up actions based on conversation context."""
    actions = []

    if intent == "emergency":
        actions.append("escalate_to_human")
        actions.append("dispatch_mobile_unit")
    elif intent == "scheduling":
        actions.append("offer_appointment_slots")
    elif intent == "price_inquiry":
        actions.append("send_price_sheet")
    elif intent == "repair_request":
        actions.append("schedule_diagnostic")

    if len(history) >= 6:  # Extended conversation
        actions.append("offer_callback")

    return actions
