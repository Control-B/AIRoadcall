"""RAG (Retrieval-Augmented Generation) Service for AI Agent Knowledge Base.

Provides formatted, context-aware mechanic and service information to the LiveKit
agent for in-call reasoning and recommendations.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.mechanic import Mechanic
from app.core.logging import get_logger
from app.utils.location import normalize_city, normalize_state

logger = get_logger(__name__)


class RAGService:
    """Service for retrieving knowledge base content for the AI agent."""

    @staticmethod
    async def get_mechanic_knowledge_base(
        db: AsyncSession,
        city: str = "",
        state: str = "",
        issue_type: str = "",
        limit: int = 10,
    ) -> str:
        """
        Retrieve formatted mechanic knowledge base for RAG context.
        
        Returns a formatted string suitable for inclusion in the LLM system prompt
        or as context for decision-making.
        """
        try:
            query = select(Mechanic).where(Mechanic.active == True)
            
            # Filter by state if provided
            if state:
                normalized_state = normalize_state(state)
                query = query.where(Mechanic.state == normalized_state)
            
            # Filter by city if state is also provided
            if city and state:
                normalized_city = normalize_city(city)
                query = query.where(Mechanic.city == normalized_city)
            
            # Order by rating and review count for better matches
            query = query.order_by(
                Mechanic.rating.desc(),
                Mechanic.review_count.desc()
            ).limit(limit)
            
            result = await db.execute(query)
            mechanics = result.scalars().all()
            
            if not mechanics:
                return f"No mechanics found in {city or 'that area'}, {state or 'that region'}."
            
            # Format as knowledge base text
            kb_lines = [
                f"📍 Available Mechanics in {city or 'the area'}, {state}:",
                ""
            ]
            
            for idx, m in enumerate(mechanics, 1):
                kb_lines.append(f"{idx}. {m.company_name}")
                
                if m.contact_name:
                    kb_lines.append(f"   Contact: {m.contact_name}")
                
                kb_lines.append(f"   Phone: {m.phone}")
                
                if m.rating:
                    kb_lines.append(f"   Rating: {m.rating}⭐ ({m.review_count or 0} reviews)")
                
                if m.service_types:
                    services = ", ".join(m.service_types[:4])
                    if len(m.service_types) > 4:
                        services += f", +{len(m.service_types) - 4} more"
                    kb_lines.append(f"   Services: {services}")
                
                if m.vehicle_types_supported:
                    vehicles = ", ".join(m.vehicle_types_supported[:3])
                    if len(m.vehicle_types_supported) > 3:
                        vehicles += f", +{len(m.vehicle_types_supported) - 3} more"
                    kb_lines.append(f"   Vehicles: {vehicles}")
                
                if m.accepts_mobile_roadside:
                    kb_lines.append(f"   Mobile: ✓ Available for roadside")
                
                if m.hours_of_operation:
                    kb_lines.append(f"   Hours: {m._format_hours()}")
                
                if m.website:
                    kb_lines.append(f"   Website: {m.website}")
                
                kb_lines.append("")
            
            return "\n".join(kb_lines)
        
        except Exception as e:
            logger.error(f"Failed to retrieve mechanic knowledge base: {e}")
            return "Could not retrieve mechanic information at this time."

    @staticmethod
    async def get_service_capabilities_kb(
        db: AsyncSession,
        issue_type: str = "",
        state: str = "",
    ) -> str:
        """
        Retrieve knowledge base of service capabilities by issue type.
        
        Useful for the agent to understand what mechanics in the area can handle.
        """
        try:
            query = select(Mechanic).where(Mechanic.active == True)
            
            if state:
                normalized_state = normalize_state(state)
                query = query.where(Mechanic.state == normalized_state)
            
            result = await db.execute(query)
            mechanics = result.scalars().all()
            
            if not mechanics:
                return "No mechanics available in that area."
            
            # Aggregate service capabilities
            services_by_capability = {}
            for m in mechanics:
                for service in (m.service_types or []):
                    if service not in services_by_capability:
                        services_by_capability[service] = []
                    services_by_capability[service].append({
                        "company": m.company_name,
                        "phone": m.phone,
                        "rating": m.rating or 0,
                    })
            
            # Format as knowledge base
            kb_lines = [
                f"🔧 Service Capabilities in {state}:",
                ""
            ]
            
            for service, providers in sorted(services_by_capability.items()):
                top_provider = max(providers, key=lambda x: x["rating"])
                kb_lines.append(f"• {service.title()}: {len(providers)} provider(s)")
                kb_lines.append(
                    f"  → Top-rated: {top_provider['company']} "
                    f"({top_provider['rating']}⭐) {top_provider['phone']}"
                )
            
            return "\n".join(kb_lines)
        
        except Exception as e:
            logger.error(f"Failed to retrieve service capabilities KB: {e}")
            return "Could not retrieve service information."

    @staticmethod
    async def get_nearby_context(
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_miles: float = 25.0,
    ) -> str:
        """
        Retrieve knowledge base of mechanics within a geographic radius.
        
        Useful for GPS-based dispatch decisions.
        """
        try:
            from app.utils.geo import haversine_distance_km
            
            # Fetch all active mechanics
            query = select(Mechanic).where(Mechanic.active == True)
            result = await db.execute(query)
            all_mechanics = result.scalars().all()
            
            # Calculate distances
            nearby = []
            for m in all_mechanics:
                if m.base_lat is None or m.base_lng is None:
                    continue
                
                dist_km = haversine_distance_km(
                    latitude, longitude,
                    m.base_lat, m.base_lng
                )
                dist_miles = dist_km * 0.621371
                
                if dist_miles <= radius_miles:
                    nearby.append((m, dist_miles))
            
            # Sort by distance
            nearby.sort(key=lambda x: x[1])
            
            if not nearby:
                return f"No mechanics found within {radius_miles} miles."
            
            # Format
            kb_lines = [
                f"📍 Mechanics within {radius_miles} miles (GPS-based):",
                ""
            ]
            
            for m, dist_miles in nearby[:10]:
                kb_lines.append(
                    f"• {m.company_name} — {dist_miles:.1f} mi away"
                )
                kb_lines.append(f"  Phone: {m.phone}, Rating: {m.rating or 'N/A'}⭐")
            
            return "\n".join(kb_lines)
        
        except Exception as e:
            logger.error(f"Failed to retrieve nearby context: {e}")
            return "Could not calculate nearby mechanics."

    @staticmethod
    async def build_system_context(
        db: AsyncSession,
        driver_city: str = "",
        driver_state: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> str:
        """
        Build a comprehensive system context for the agent from available mechanics.
        
        This can be prepended to the system prompt or used as dynamic context.
        """
        context_parts = [
            "🛠️ MECHANIC NETWORK KNOWLEDGE BASE:",
            ""
        ]
        
        # Geographic context
        if latitude is not None and longitude is not None:
            nearby_kb = await RAGService.get_nearby_context(db, latitude, longitude)
            context_parts.extend([nearby_kb, ""])
        
        # City/State context
        if driver_city and driver_state:
            location_kb = await RAGService.get_mechanic_knowledge_base(
                db, driver_city, driver_state, limit=8
            )
            context_parts.extend([location_kb, ""])
            
            # Service capabilities in that state
            services_kb = await RAGService.get_service_capabilities_kb(db, state=driver_state)
            context_parts.extend([services_kb, ""])
        
        return "\n".join(context_parts)
