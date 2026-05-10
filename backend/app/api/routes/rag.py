"""API routes for RAG (Retrieval-Augmented Generation) knowledge base queries."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin_api_key
from app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get(
    "/mechanics",
    response_model=str,
    dependencies=[Depends(require_admin_api_key)],
)
async def get_mechanic_knowledge_base(
    city: str = Query(default=""),
    state: str = Query(default=""),
    issue_type: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_session),
):
    """
    Retrieve formatted mechanic knowledge base for AI agent context.
    
    Returns a plain text knowledge base suitable for LLM prompts or dynamic context.
    Use this to feed the agent with up-to-date information about available mechanics.
    """
    if not state:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="state is required",
        )
    
    kb_text = await RAGService.get_mechanic_knowledge_base(
        db,
        city=city,
        state=state,
        issue_type=issue_type,
        limit=limit,
    )
    return kb_text


@router.get(
    "/services",
    response_model=str,
    dependencies=[Depends(require_admin_api_key)],
)
async def get_service_capabilities(
    state: str = Query(default=""),
    issue_type: str = Query(default=""),
    db: AsyncSession = Depends(get_session),
):
    """
    Retrieve knowledge base of service capabilities by type in a state.
    
    Helps the agent understand what services are available and who provides them best.
    """
    if not state:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="state is required",
        )
    
    kb_text = await RAGService.get_service_capabilities_kb(db, issue_type=issue_type, state=state)
    return kb_text


@router.get(
    "/nearby",
    response_model=str,
    dependencies=[Depends(require_admin_api_key)],
)
async def get_nearby_mechanics_context(
    latitude: float = Query(default=...),
    longitude: float = Query(default=...),
    radius_miles: float = Query(default=25.0, ge=1.0, le=100.0),
    db: AsyncSession = Depends(get_session),
):
    """
    Retrieve knowledge base of mechanics within a geographic radius.
    
    GPS-based context for the agent to make informed dispatch decisions.
    """
    kb_text = await RAGService.get_nearby_context(
        db,
        latitude=latitude,
        longitude=longitude,
        radius_miles=radius_miles,
    )
    return kb_text


@router.get(
    "/context",
    response_model=str,
    dependencies=[Depends(require_admin_api_key)],
)
async def build_system_context(
    driver_city: str = Query(default=""),
    driver_state: str = Query(default=""),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
):
    """
    Build comprehensive system context for the agent.
    
    Combines all available knowledge (geographic, service capabilities, etc.) 
    into a single formatted context string suitable for prepending to the LLM system prompt.
    """
    if not driver_state:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="driver_state is required",
        )
    
    context = await RAGService.build_system_context(
        db,
        driver_city=driver_city,
        driver_state=driver_state,
        latitude=latitude,
        longitude=longitude,
    )
    return context
