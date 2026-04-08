"""Data Pipeline Routes — Manage mechanic data ingestion and enrichment.

Endpoints for:
  - Triggering Apify scrapes (bulk mechanic discovery)
  - Checking scrape status and importing results
  - Running Tavily enrichment (batch or targeted)
  - Viewing pipeline statistics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.mechanic import (
    ScrapeRequest,
    ScrapeStatusView,
    EnrichRequest,
    EnrichResultView,
    PipelineStatsView,
)
from app.services.apify_service import ApifyService
from app.services.tavily_service import TavilyService
from app.services.mechanic_data_service import MechanicDataService

router = APIRouter(prefix="/pipeline", tags=["data-pipeline"])

apify_service = ApifyService()
tavily_service = TavilyService()


# ── Apify Scrape Endpoints ───────────────────────────────


@router.post("/scrape", response_model=ScrapeStatusView)
async def start_scrape(request: ScrapeRequest):
    """Start a new Apify scrape for mechanics in the given area.

    This triggers a Google Maps scrape. It runs asynchronously on Apify's
    infrastructure. Use GET /pipeline/scrape/{run_id} to check status,
    then POST /pipeline/scrape/{run_id}/import to import results.
    """
    try:
        result = await apify_service.start_scrape(
            location=request.location,
            radius_miles=request.radius_miles,
            max_results=request.max_results,
        )
        return ScrapeStatusView(
            run_id=result["run_id"],
            status=result["status"],
            started_at=result.get("started_at"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Apify API error: {e}")


@router.get("/scrape/{run_id}", response_model=ScrapeStatusView)
async def get_scrape_status(run_id: str):
    """Check the status of an Apify scrape run."""
    try:
        result = await apify_service.get_run_status(run_id)
        return ScrapeStatusView(
            run_id=result["run_id"],
            status=result["status"],
            started_at=result.get("started_at"),
            finished_at=result.get("finished_at"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Apify API error: {e}")


@router.post("/scrape/{run_id}/import")
async def import_scrape_results(
    run_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Import results from a completed Apify scrape into the mechanic database.

    This fetches the dataset from Apify, parses each result, and upserts
    mechanics by phone number. Returns stats on what was imported.
    """
    try:
        raw_items = await apify_service.fetch_results(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Apify API error: {e}")

    upserted = 0
    skipped = 0
    errors = []

    for item in raw_items:
        parsed = apify_service.parse_result(item)
        if not parsed:
            skipped += 1
            continue

        try:
            await MechanicDataService.upsert_mechanic(db, parsed)
            upserted += 1
        except Exception as e:
            errors.append({"name": item.get("title", "?"), "error": str(e)})

    await db.commit()

    return {
        "run_id": run_id,
        "total_items": len(raw_items),
        "upserted": upserted,
        "skipped": skipped,
        "errors": errors[:10],  # Cap error list
    }


# ── Tavily Enrichment Endpoints ──────────────────────────


@router.post("/enrich", response_model=list[EnrichResultView])
async def enrich_mechanics(
    request: EnrichRequest,
    db: AsyncSession = Depends(get_session),
):
    """Enrich mechanic records using Tavily AI search.

    Two modes:
    - **Targeted**: Provide mechanic_ids to enrich specific records
    - **Stale**: Omit mechanic_ids to auto-enrich records that haven't
      been verified in `max_age_hours` (default 7 days)
    """
    if request.mechanic_ids:
        results = await tavily_service.enrich_by_ids(db, request.mechanic_ids)
    else:
        results = await tavily_service.enrich_stale_mechanics(
            db,
            max_age_hours=request.max_age_hours,
            limit=request.limit,
        )

    await db.commit()
    return results


# ── Pipeline Stats ───────────────────────────────────────


@router.get("/stats", response_model=PipelineStatsView)
async def get_pipeline_stats(db: AsyncSession = Depends(get_session)):
    """Get aggregate statistics about the mechanic database.

    Returns counts, source breakdown, enrichment freshness, and
    dispatch performance metrics.
    """
    stats = await MechanicDataService.get_pipeline_stats(db)
    return PipelineStatsView(**stats)
