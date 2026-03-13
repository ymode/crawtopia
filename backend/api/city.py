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
from backend.models.directive import Directive
from backend.models.task import Task
from backend.models.city_event import CityEvent
from backend.config import get_settings

router = APIRouter()


@router.get("/status")
async def city_status(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    active_agents = (await db.execute(
        select(func.count(Agent.id)).where(Agent.status == "active")
    )).scalar() or 0

    total_agents = (await db.execute(
        select(func.count(Agent.id))
    )).scalar() or 0

    total_roles = (await db.execute(
        select(func.count(Role.id))
    )).scalar() or 0

    filled_roles = (await db.execute(
        select(func.count(RoleAssignment.id)).where(
            (RoleAssignment.expires_at.is_(None))
            | (RoleAssignment.expires_at > datetime.now(timezone.utc))
        )
    )).scalar() or 0

    active_elections = (await db.execute(
        select(func.count(Election.id)).where(
            Election.status.in_(["scheduled", "nominating", "voting", "counting"])
        )
    )).scalar() or 0

    enacted_laws = (await db.execute(
        select(func.count(Law.id)).where(Law.status == "enacted")
    )).scalar() or 0

    constitution_count = (await db.execute(
        select(func.count(ConstitutionArticle.id))
    )).scalar() or 0

    active_directives = (await db.execute(
        select(func.count(Directive.id)).where(Directive.status == "active")
    )).scalar() or 0

    open_tasks = (await db.execute(
        select(func.count(Task.id)).where(Task.status == "open")
    )).scalar() or 0

    # Top directive for quick reference
    top_directive_result = await db.execute(
        select(Directive)
        .where(Directive.status == "active")
        .order_by(Directive.priority.desc())
        .limit(1)
    )
    top_directive = top_directive_result.scalar_one_or_none()

    has_constitution = constitution_count > 1
    has_government = filled_roles > 0

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
            "active_agents": active_agents,
            "total_agents": total_agents,
            "total_roles": total_roles,
            "filled_roles": filled_roles,
            "active_elections": active_elections,
            "enacted_laws": enacted_laws,
            "constitution_articles": constitution_count,
            "active_directives": active_directives,
            "open_tasks": open_tasks,
        },
        "config": {
            "election_cycle_hours": settings.election_cycle_hours,
            "founding_senate_size": settings.founding_senate_size,
            "senate_seats": settings.senate_seats,
        },
        "top_directive": {
            "title": top_directive.title,
            "priority": top_directive.priority,
            "division": top_directive.division,
        } if top_directive else None,
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
