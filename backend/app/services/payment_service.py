import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.payment import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentConfirmResponse,
)
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.audit_service import AuditService

logger = get_logger(__name__)
settings = get_settings()

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:

    @staticmethod
    async def create_payment_intent(
        db: AsyncSession, job: Job, request: PaymentIntentRequest
    ) -> PaymentIntentResponse:
        """Create a Stripe PaymentIntent with manual capture for authorization hold."""
        amount_dollars = request.amount or (
            float(job.payment_hold_amount) if job.payment_hold_amount else 150.00
        )
        amount_cents = int(amount_dollars * 100)

        # Create Stripe PaymentIntent with manual capture
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            capture_method="manual",
            metadata={
                "public_job_id": job.public_job_id,
                "driver_phone": job.driver_phone,
            },
        )

        job.stripe_payment_intent_id = intent.id
        job.payment_status = PaymentStatus.pending
        job.payment_hold_amount = amount_dollars
        await db.flush()

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="payment.intent_created",
            actor_type="system",
            payload={
                "payment_intent_id": intent.id,
                "amount_cents": amount_cents,
            },
        )

        logger.info(
            f"PaymentIntent created for job {job.public_job_id}: {intent.id}"
        )

        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
            amount=amount_dollars,
            currency="usd",
            status=intent.status,
        )

    @staticmethod
    async def confirm_payment_authorization(
        db: AsyncSession, job: Job, payment_intent_id: str
    ) -> PaymentConfirmResponse:
        """Confirm that the frontend completed payment authorization."""
        # Verify with Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent.status == "requires_capture":
            job.payment_status = PaymentStatus.authorized
            job.status = JobStatus.payment_authorized

            await AuditService.log(
                db,
                job_id=job.id,
                event_type="payment.authorized",
                actor_type="stripe",
                payload={"payment_intent_id": payment_intent_id},
            )
            await AuditService.log(
                db,
                job_id=job.id,
                event_type="job.status_changed",
                actor_type="system",
                payload={
                    "from": JobStatus.awaiting_payment_authorization,
                    "to": JobStatus.payment_authorized,
                },
            )
        elif intent.status == "succeeded":
            # Auto-capture happened (shouldn't with manual capture, but handle it)
            job.payment_status = PaymentStatus.captured
            job.status = JobStatus.payment_authorized
        else:
            job.payment_status = PaymentStatus.failed

            await AuditService.log(
                db,
                job_id=job.id,
                event_type="payment.failed",
                actor_type="stripe",
                payload={
                    "payment_intent_id": payment_intent_id,
                    "stripe_status": intent.status,
                },
            )

        await db.flush()
        logger.info(
            f"Payment confirmation for job {job.public_job_id}: {job.payment_status}"
        )

        # ── Auto-trigger dispatch when payment is authorized ──
        if job.status == JobStatus.payment_authorized and job.driver_lat and job.driver_lng:
            try:
                from app.services.dispatch_service import DispatchService

                await DispatchService.start_dispatch(db, job.id)
                next_mechanic = await DispatchService.dispatch_next_mechanic(db, job.id)
                if next_mechanic:
                    logger.info(
                        f"Auto-dispatch triggered for job {job.public_job_id}: "
                        f"{next_mechanic.mechanic_company} ({next_mechanic.mechanic_phone})"
                    )
                    # Initiate outbound call to the mechanic via LiveKit SIP
                    from app.services.livekit_service import LiveKitService
                    await LiveKitService.initiate_mechanic_call(
                        mechanic_phone=next_mechanic.mechanic_phone,
                        mechanic_name=next_mechanic.mechanic_company,
                        job_summary=f"{job.issue_type}: {job.issue_summary or ''} — {job.vehicle_type or 'vehicle'}",
                        job_id=str(job.id),
                        dispatch_attempt_id=next_mechanic.dispatch_attempt_id,
                    )
                else:
                    logger.warning(f"No mechanics available for job {job.public_job_id}")
            except Exception as e:
                logger.error(f"Auto-dispatch failed for {job.public_job_id}: {e}")

        return PaymentConfirmResponse(
            success=job.payment_status in (PaymentStatus.authorized, PaymentStatus.captured),
            payment_status=job.payment_status,
            job_status=job.status,
        )

    @staticmethod
    async def handle_stripe_event(
        db: AsyncSession, event_type: str, payment_intent: dict
    ) -> None:
        """Process Stripe webhook events idempotently."""
        from sqlalchemy import select

        pi_id = payment_intent.get("id")
        if not pi_id:
            return

        result = await db.execute(
            select(Job).where(Job.stripe_payment_intent_id == pi_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            logger.warning(f"Stripe webhook: no job found for PI {pi_id}")
            return

        if event_type == "payment_intent.amount_capturable_updated":
            if job.payment_status != PaymentStatus.authorized:
                job.payment_status = PaymentStatus.authorized
                if job.status == JobStatus.awaiting_payment_authorization:
                    job.status = JobStatus.payment_authorized

        elif event_type == "payment_intent.succeeded":
            job.payment_status = PaymentStatus.captured

        elif event_type in ("payment_intent.payment_failed", "payment_intent.canceled"):
            job.payment_status = PaymentStatus.failed

        await AuditService.log(
            db,
            job_id=job.id,
            event_type=f"stripe.{event_type}",
            actor_type="stripe",
            actor_id=pi_id,
            payload={"stripe_status": payment_intent.get("status")},
        )

        await db.flush()
        logger.info(f"Stripe webhook processed: {event_type} for PI {pi_id}")
