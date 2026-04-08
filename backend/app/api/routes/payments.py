from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, validate_magic_token
from app.schemas.payment import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentConfirmRequest,
    PaymentConfirmResponse,
)
from app.services.payment_service import PaymentService
from app.enums.job_status import JobStatus

router = APIRouter(prefix="/jobs", tags=["payments"])


@router.post("/{token}/payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    token: str,
    request: PaymentIntentRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create a Stripe PaymentIntent with manual capture for authorization hold."""
    job = await validate_magic_token(token, db)

    if job.status not in (
        JobStatus.awaiting_payment_authorization,
        JobStatus.awaiting_driver_location,  # Allow re-creation
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create payment intent in job status: {job.status}",
        )

    return await PaymentService.create_payment_intent(db, job, request)


@router.post("/{token}/payment-confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    token: str,
    request: PaymentConfirmRequest,
    db: AsyncSession = Depends(get_session),
):
    """Confirm that the frontend completed payment authorization."""
    job = await validate_magic_token(token, db)

    if not job.stripe_payment_intent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No payment intent found for this job",
        )

    if job.stripe_payment_intent_id != request.payment_intent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment intent ID mismatch",
        )

    return await PaymentService.confirm_payment_authorization(
        db, job, request.payment_intent_id
    )
