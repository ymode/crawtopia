"""City directives - high-level goals set by the Senate, approved by the President."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.directive import Directive
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.core.agent_manager import AgentManager
from backend.schemas.directive import DirectivePropose, DirectivePublic

router = APIRouter()


async def _enrich(directive: Directive, db) -> DirectivePublic:
    data = DirectivePublic.model_validate(directive)
    proposer = (await db.execute(
        select(Agent.name).where(Agent.id == directive.proposed_by)
    )).scalar()
    data.proposer_name = proposer or "Unknown"
    if directive.approved_by:
        approver = (await db.execute(
            select(Agent.name).where(Agent.id == directive.approved_by)
        )).scalar()
        data.approver_name = approver or ""
    return data


@router.get("/", response_model=list[DirectivePublic])
async def list_directives(
    status: str | None = None,
    division: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Directive).order_by(Directive.priority.desc(), Directive.created_at.desc())
    if status:
        query = query.where(Directive.status == status)
    if division:
        query = query.where(Directive.division == division)
    result = await db.execute(query)
    return [await _enrich(d, db) for d in result.scalars().all()]


@router.get("/active", response_model=list[DirectivePublic])
async def active_directives(
    division: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Directive)
        .where(Directive.status == "active")
        .order_by(Directive.priority.desc(), Directive.created_at.asc())
    )
    if division:
        query = query.where(Directive.division == division)
    result = await db.execute(query)
    return [await _enrich(d, db) for d in result.scalars().all()]


@router.post("/", response_model=DirectivePublic, status_code=201)
async def propose_directive(
    payload: DirectivePropose,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    if not await mgr.is_senator(agent.id):
        raise HTTPException(status_code=403, detail="Only senators can propose directives")

    directive = Directive(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        division=payload.division,
        proposed_by=agent.id,
    )
    db.add(directive)

    event = CityEvent(
        event_type="directive_proposed",
        data={"title": payload.title, "priority": payload.priority, "by": str(agent.id)},
    )
    db.add(event)

    await db.flush()
    return await _enrich(directive, db)


@router.post("/{directive_id}/approve", response_model=DirectivePublic)
async def approve_directive(
    directive_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    if not await mgr.is_president(agent.id):
        raise HTTPException(status_code=403, detail="Only the president can approve directives")

    import uuid
    result = await db.execute(
        select(Directive).where(Directive.id == uuid.UUID(directive_id))
    )
    directive = result.scalar_one_or_none()
    if not directive:
        raise HTTPException(status_code=404, detail="Directive not found")
    if directive.status != "proposed":
        raise HTTPException(status_code=400, detail=f"Directive is not pending approval (status: {directive.status})")

    directive.status = "active"
    directive.approved_by = agent.id
    directive.approved_at = datetime.now(timezone.utc)
    db.add(directive)

    event = CityEvent(
        event_type="directive_approved",
        data={"title": directive.title, "directive_id": str(directive.id), "by": str(agent.id)},
    )
    db.add(event)

    await db.flush()
    return await _enrich(directive, db)


@router.post("/{directive_id}/complete", response_model=DirectivePublic)
async def complete_directive(
    directive_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    is_gov = await mgr.is_senator(agent.id) or await mgr.is_president(agent.id)
    if not is_gov:
        raise HTTPException(status_code=403, detail="Only government officials can complete directives")

    import uuid
    result = await db.execute(
        select(Directive).where(Directive.id == uuid.UUID(directive_id))
    )
    directive = result.scalar_one_or_none()
    if not directive:
        raise HTTPException(status_code=404, detail="Directive not found")
    if directive.status != "active":
        raise HTTPException(status_code=400, detail="Only active directives can be completed")

    directive.status = "completed"
    directive.completed_at = datetime.now(timezone.utc)
    db.add(directive)

    event = CityEvent(
        event_type="directive_completed",
        data={"title": directive.title, "directive_id": str(directive.id), "by": str(agent.id)},
    )
    db.add(event)

    await db.flush()
    return await _enrich(directive, db)
