"""City-wide status and event endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.role import Role, RoleAssignment
from backend.models.election import Election
from backend.models.governance import Law, ConstitutionArticle
from backend.models.city_event import CityEvent
from backend.config import get_settings

router = APIRouter()


@router.get("/status")
async def city_status(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    agents_count = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == "active")
    )
    total_agents = await db.execute(select(func.count(Agent.id)))
    total_roles = await db.execute(select(func.count(Role.id)))
    filled_roles = await db.execute(
        select(func.count(RoleAssignment.id)).where(
            (RoleAssignment.expires_at.is_(None))
            | (RoleAssignment.expires_at > datetime.now(timezone.utc))
        )
    )
    active_elections = await db.execute(
        select(func.count(Election.id)).where(
            Election.status.in_(["scheduled", "nominating", "voting", "counting"])
        )
    )
    enacted_laws = await db.execute(
        select(func.count(Law.id)).where(Law.status == "enacted")
    )
    constitution_articles = await db.execute(
        select(func.count(ConstitutionArticle.id))
    )

    # Determine city phase
    has_constitution = (constitution_articles.scalar() or 0) > 1
    has_government = (filled_roles.scalar() or 0) > 0

    if not has_government:
        phase = "awaiting_founding"
    elif not has_constitution:
        phase = "founding"
    else:
        phase = "operational"

    return {
        "city": settings.city_name,
        "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "active_agents": agents_count.scalar() or 0,
            "total_agents": total_agents.scalar() or 0,
            "total_roles": total_roles.scalar() or 0,
            "filled_roles": filled_roles.scalar() or 0,
            "active_elections": active_elections.scalar() or 0,
            "enacted_laws": enacted_laws.scalar() or 0,
            "constitution_articles": constitution_articles.scalar() or 0,
        },
        "config": {
            "election_cycle_hours": settings.election_cycle_hours,
            "founding_senate_size": settings.founding_senate_size,
        },
    }


@router.get("/events")
async def city_events(
    limit: int = 50,
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(CityEvent).order_by(CityEvent.created_at.desc()).limit(limit)
    if event_type:
        query = query.where(CityEvent.event_type == event_type)
    result = await db.execute(query)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "data": e.data,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
