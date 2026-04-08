import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.dispatch import (
    DispatchStartResponse,
    DispatchNextResponse,
    MechanicResponseRequest,
    MechanicResponseResponse,
)
from app.services.dispatch_service import DispatchService

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


@router.post("/{job_id}/start", response_model=DispatchStartResponse)
async def start_dispatch(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Begin mechanic matching and dispatch workflow.

    Only allowed if payment is authorized. Called by backend orchestration
    after payment confirmation.
    """
    try:
        return await DispatchService.start_dispatch(db, job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{job_id}/next", response_model=DispatchNextResponse)
async def dispatch_next_mechanic(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Select and queue the next best-ranked mechanic for dispatch."""
    try:
        result = await DispatchService.dispatch_next_mechanic(db, job_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No more available mechanics for this job",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{job_id}/mechanic-response", response_model=MechanicResponseResponse)
async def record_mechanic_response(
    job_id: uuid.UUID,
    request: MechanicResponseRequest,
    db: AsyncSession = Depends(get_session),
):
    """Record a mechanic's response to a dispatch attempt."""
    try:
        return await DispatchService.record_mechanic_response(
            db=db,
            job_id=job_id,
            attempt_id=uuid.UUID(request.dispatch_attempt_id),
            response=request.response,
            eta_minutes=request.eta_minutes,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
