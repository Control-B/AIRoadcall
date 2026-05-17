import stripe
from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.deps import get_session
from app.services.payment_service import PaymentService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.organization import Organization
from app.services.lifecycle_service import LifecycleService
from app.services.subscription_billing_service import SubscriptionBillingService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()
logger = get_logger(__name__)
lifecycle_service = LifecycleService()
billing_service = SubscriptionBillingService()


STRIPE_LIFECYCLE_EVENT_MAP = {
    "checkout.session.completed": "checkout_completed",
    "customer.subscription.created": "subscription_started",
    "customer.subscription.updated": "subscription_updated",
    "customer.subscription.deleted": "subscription_cancelled",
    "invoice.payment_succeeded": "invoice_paid",
    "invoice.payment_failed": "payment_failed",
    "payment_intent.payment_failed": "payment_failed",
    "payment_intent.succeeded": "invoice_paid",
}


def _stripe_object_to_dict(data_object) -> dict:
    if hasattr(data_object, "to_dict_recursive"):
        return data_object.to_dict_recursive()
    return dict(data_object)


async def _resolve_organization_id(db: AsyncSession, data_object) -> uuid.UUID | None:
    metadata = data_object.get("metadata") or {}
    for key in ("organization_id", "roadcall_organization_id", "org_id"):
        value = metadata.get(key)
        if value:
            try:
                return uuid.UUID(str(value))
            except ValueError:
                continue

    customer_details = data_object.get("customer_details") or {}
    email = (
        data_object.get("customer_email")
        or data_object.get("receipt_email")
        or customer_details.get("email")
    )
    if email:
        result = await db.execute(select(Organization).where(Organization.contact_email == str(email).lower()))
        org = result.scalar_one_or_none()
        if org:
            return org.id
    return None


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Handle Stripe webhook events with signature verification and idempotency."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    event_type = event["type"]
    data_object = event["data"]["object"]

    handled_events = {
        "payment_intent.amount_capturable_updated",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
    }

    payment_handled = event_type in handled_events
    lifecycle_handled = event_type in STRIPE_LIFECYCLE_EVENT_MAP

    if payment_handled:
        await PaymentService.handle_stripe_event(db, event_type, data_object)
        logger.info(f"Stripe webhook handled: {event_type}")
    if lifecycle_handled:
        if event_type == "checkout.session.completed":
            await billing_service.sync_checkout_completed(db, _stripe_object_to_dict(data_object))
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            await billing_service.sync_subscription(db, _stripe_object_to_dict(data_object))
        organization_id = await _resolve_organization_id(db, data_object)
        await lifecycle_service.emit_event(
            db,
            event_type=STRIPE_LIFECYCLE_EVENT_MAP[event_type],
            source="stripe",
            organization_id=organization_id,
            entity_type=str(data_object.get("object") or "stripe_event"),
            entity_id=str(data_object.get("id") or event.get("id") or ""),
            payload={
                "stripe_event_id": event.get("id"),
                "stripe_event_type": event_type,
                "stripe_object": _stripe_object_to_dict(data_object),
            },
            idempotency_key=f"stripe:{event.get('id')}",
        )
        await db.commit()
        logger.info(f"Stripe lifecycle event recorded: {event_type}")
    if not payment_handled and not lifecycle_handled:
        logger.info(f"Stripe webhook ignored: {event_type}")

    return {"received": True}
