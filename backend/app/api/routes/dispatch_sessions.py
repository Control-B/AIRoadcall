import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.roadside import require_roadside_match_access
from app.schemas.dispatch_session import (
    ActiveCallContextRequest,
    ActiveCallContextResponse,
    DispatchCreateSessionRequest,
    DispatchCreateSessionResponse,
    DispatchLinkCaseCodeRequest,
    DispatchLinkCaseCodeResponse,
    DispatchSessionStatusRequest,
    DispatchSessionStatusResponse,
    DispatchUpdateLocationRequest,
    DispatchUpdateLocationResponse,
)
from app.services.dispatch_session_service import DispatchSessionService

router = APIRouter(prefix="/dispatch", tags=["dispatch-sessions"])


@router.post(
    "/active-call-context",
    response_model=ActiveCallContextResponse,
    dependencies=[Depends(require_roadside_match_access)],
)
async def active_call_context(
    payload: ActiveCallContextRequest,
    db: AsyncSession = Depends(get_session),
):
    return await DispatchSessionService.active_call_context(db, payload)


@router.post(
    "/create-session",
    response_model=DispatchCreateSessionResponse,
    dependencies=[Depends(require_roadside_match_access)],
)
async def create_dispatch_session(
    payload: DispatchCreateSessionRequest,
    db: AsyncSession = Depends(get_session),
):
    return await DispatchSessionService.create_session(db, payload)


@router.post("/update-location", response_model=DispatchUpdateLocationResponse)
async def update_dispatch_location(
    payload: DispatchUpdateLocationRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        return await DispatchSessionService.update_location(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get(
    "/session-status/{dispatch_session_id}",
    response_model=DispatchSessionStatusResponse,
    dependencies=[Depends(require_roadside_match_access)],
)
async def dispatch_session_status(
    dispatch_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    session = await DispatchSessionService.get_session(db, dispatch_session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch session not found")
    return await DispatchSessionService.status_response(db, session)


@router.post(
    "/session-status",
    response_model=DispatchSessionStatusResponse,
    dependencies=[Depends(require_roadside_match_access)],
)
async def dispatch_session_status_post(
    payload: DispatchSessionStatusRequest,
    db: AsyncSession = Depends(get_session),
):
    session = await DispatchSessionService.get_session(db, payload.dispatch_session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch session not found")
    return await DispatchSessionService.status_response(db, session)


@router.post("/link-case-code", response_model=DispatchLinkCaseCodeResponse)
async def link_case_code(
    payload: DispatchLinkCaseCodeRequest,
    x_roadcall_case_code_rate_limit: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
):
    del x_roadcall_case_code_rate_limit
    try:
        return await DispatchSessionService.link_case_code(
            db,
            payload.public_code,
            payload.caller_phone_last4,
            payload.expires_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc