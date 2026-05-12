"""Major chain vendor lookup + bootstrap.

Sits next to the local mechanic matching service. Returns one nearby
national-chain truck-service location (Love's, TA/Petro, Pilot/FJ, Speedco,
Rush, FleetPride, Southern Tire Mart, Boss Truck Shops) so the dispatcher can
always present "3 local mechanics and 1 major vendor".

Designed to be additive — does NOT modify existing Mechanic / Vendor flows.
"""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.data.major_vendor_seed import MAJOR_VENDOR_SEED
from app.models.major_vendor_location import MajorVendorLocation
from app.utils.geo import haversine_distance_km

logger = get_logger(__name__)


# ── capability filter ────────────────────────────────────────────────
def _capability_filter(vehicle: str | None, problem: str | None) -> dict[str, bool]:
    """Map caller vehicle/problem to required capability flags on vendor row."""
    needs: dict[str, bool] = {}
    v = (vehicle or "").lower()
    p = (problem or "").lower()

    if "rv" in v or "motorhome" in v or "camper" in v:
        needs["rv_service"] = True
    elif "semi" in v or "heavy" in v or "tractor" in v or "18" in v or "fleet" in v or "trailer" in v or "commercial" in v:
        needs["heavy_duty"] = True

    if "tow" in p:
        needs["towing"] = True
    elif "tire" in p or "flat" in p:
        needs["tire_service"] = True
    return needs


def _row_matches_capability(row: MajorVendorLocation, needs: dict[str, bool]) -> bool:
    for attr, required in needs.items():
        if required and not bool(getattr(row, attr, False)):
            return False
    return True


# ── lookup ───────────────────────────────────────────────────────────
class MajorVendorService:
    """Find the best major-chain vendor for a roadside caller."""

    @staticmethod
    async def find_nearest(
        db: AsyncSession,
        *,
        state: str | None,
        latitude: float | None,
        longitude: float | None,
        vehicle: str | None = None,
        problem: str | None = None,
    ) -> tuple[MajorVendorLocation, float | None] | None:
        """Return (vendor, distance_miles) or None.

        - Always restrict to same state when provided.
        - When lat/lng available, rank by haversine and require capability.
        - When lat/lng not available, fall back to highest priority_score.
        """
        if not state:
            return None

        stmt = select(MajorVendorLocation).where(
            MajorVendorLocation.active == True,  # noqa: E712
            func.upper(MajorVendorLocation.state) == state.upper(),
        ).limit(500)
        result = await db.execute(stmt)
        rows: list[MajorVendorLocation] = list(result.scalars().all())
        if not rows:
            return None

        needs = _capability_filter(vehicle, problem)
        capable = [r for r in rows if _row_matches_capability(r, needs)] or rows

        if latitude is not None and longitude is not None:
            ranked: list[tuple[MajorVendorLocation, float]] = []
            for row in capable:
                if row.latitude is None or row.longitude is None:
                    continue
                miles = haversine_distance_km(
                    float(latitude), float(longitude),
                    float(row.latitude), float(row.longitude),
                ) * 0.621371
                ranked.append((row, miles))
            if ranked:
                ranked.sort(key=lambda t: (t[1], -t[0].priority_score))
                return ranked[0]

        capable.sort(key=lambda r: -r.priority_score)
        return capable[0], None

    @staticmethod
    async def bootstrap_seed(db: AsyncSession, seed: Iterable[dict[str, Any]] | None = None) -> dict[str, int]:
        """Idempotently upsert MAJOR_VENDOR_SEED rows. Returns counts."""
        rows = list(seed if seed is not None else MAJOR_VENDOR_SEED)
        inserted = 0
        updated = 0
        for entry in rows:
            brand = entry.get("brand_name")
            address = entry.get("address")
            city = entry.get("city")
            state = entry.get("state")
            if not (brand and city and state):
                continue
            existing_q = select(MajorVendorLocation).where(
                and_(
                    MajorVendorLocation.brand_name == brand,
                    MajorVendorLocation.city == city,
                    MajorVendorLocation.state == state,
                    MajorVendorLocation.address == address,
                )
            )
            existing = (await db.execute(existing_q)).scalar_one_or_none()
            if existing:
                for key, value in entry.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                db.add(MajorVendorLocation(**{
                    k: v for k, v in entry.items()
                    if hasattr(MajorVendorLocation, k)
                }))
                inserted += 1
        await db.commit()
        logger.info("major_vendor_seed_bootstrap inserted=%d updated=%d", inserted, updated)
        return {"inserted": inserted, "updated": updated, "total": len(rows)}
