"""Admin diagnostics + ops endpoints for the major chain vendor layer."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.major_vendor_location import MajorVendorLocation
from app.services.major_vendor_service import MajorVendorService

router = APIRouter(prefix="/admin/major-vendors", tags=["admin", "major-vendors"])
logger = get_logger(__name__)


def _require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    admin_key = (settings.ADMIN_API_KEY or "").strip()
    if not admin_key or not x_admin_key or x_admin_key.strip() != admin_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="admin key required")


@router.get("/stats", dependencies=[Depends(_require_admin)])
async def stats(db: AsyncSession = Depends(get_session)):
    """How many chain locations are loaded, broken down by brand and state."""
    total = (await db.execute(select(func.count()).select_from(MajorVendorLocation))).scalar_one()
    by_brand = (await db.execute(
        select(MajorVendorLocation.brand_name, func.count())
        .group_by(MajorVendorLocation.brand_name)
        .order_by(func.count().desc())
    )).all()
    by_state = (await db.execute(
        select(MajorVendorLocation.state, func.count())
        .group_by(MajorVendorLocation.state)
        .order_by(func.count().desc())
    )).all()
    return {
        "total": total,
        "brands": {b: c for b, c in by_brand},
        "states": {s: c for s, c in by_state},
    }


@router.post("/seed-bootstrap", dependencies=[Depends(_require_admin)])
async def seed_bootstrap(db: AsyncSession = Depends(get_session)):
    """Re-run the curated MAJOR_VENDOR_SEED upsert. Idempotent."""
    return await MajorVendorService.bootstrap_seed(db)
