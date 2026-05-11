from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.roadside_match import RoadsideMatchRequest, RoadsideMatchResponse
from app.services.roadside_matching_service import RoadsideMatchingService

router = APIRouter(prefix="/roadside", tags=["roadside"])
logger = get_logger(__name__)


async def require_roadside_match_access(
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    admin_key = settings.ADMIN_API_KEY.strip()
    if admin_key and x_admin_key and x_admin_key.strip() == admin_key:
        return

    retell_token = settings.RETELL_BACKEND_WEBHOOK_TOKEN.strip()
    expected_bearer = f"Bearer {retell_token}"
    if retell_token and authorization and authorization.strip() == expected_bearer:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authorized to match mechanics",
    )


@router.post(
    "/match-mechanic",
    response_model=RoadsideMatchResponse,
    dependencies=[Depends(require_roadside_match_access)],
)
async def match_mechanic(
    request: RoadsideMatchRequest,
    db: AsyncSession = Depends(get_session),
):
    """Match a caller/driver to the best nearby mechanics using location + problem context.

    Retell wraps the body as {"name", "args", "call"} — the global middleware in
    app.main unwraps that envelope so this handler always sees the flat args.
    """
    try:
        return await RoadsideMatchingService.match_mechanic(db, request)
    except Exception as exc:
        logger.exception("roadside_match_api_error fallback_to_manual_dispatch error=%s", exc)
        context = RoadsideMatchingService.build_context(request)
        return RoadsideMatchResponse(
            status="manual_dispatch_required",
            searchLevel="api_error_fallback",
            matches=[],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=context,
            callerLocation=context,
            fallbackEscalation=True,
            fallbackCreated=True,
            message="I’m having trouble checking the database, but I can still create a dispatch request.",
        )
