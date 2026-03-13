import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.role import Role, RoleAssignment
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.schemas.role import RolePublic, RoleApply, RoleApplyResponse, DivisionSummary

router = APIRouter()


@router.get("/", response_model=list[RolePublic])
async def list_roles(
    division: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Role).order_by(Role.division, Role.name)
    if division:
        query = query.where(Role.division == division)
    result = await db.execute(query)
    roles = result.scalars().all()

    response = []
    for role in roles:
        filled = await db.execute(
            select(func.count(RoleAssignment.id))
            .where(RoleAssignment.role_id == role.id)
            .where(
                (RoleAssignment.expires_at.is_(None))
                | (RoleAssignment.expires_at > datetime.now(timezone.utc))
            )
        )
        filled_count = filled.scalar() or 0

        role_data = RolePublic.model_validate(role)
        role_data.filled_slots = filled_count
        response.append(role_data)

    return response


@router.get("/divisions", response_model=list[DivisionSummary])
async def list_divisions(db: AsyncSession = Depends(get_db)):
    roles_result = await db.execute(select(Role).order_by(Role.division, Role.name))
    all_roles = roles_result.scalars().all()

    divisions: dict[str, DivisionSummary] = {}
    for role in all_roles:
        filled = await db.execute(
            select(func.count(RoleAssignment.id))
            .where(RoleAssignment.role_id == role.id)
            .where(
                (RoleAssignment.expires_at.is_(None))
                | (RoleAssignment.expires_at > datetime.now(timezone.utc))
            )
        )
        filled_count = filled.scalar() or 0

        role_pub = RolePublic.model_validate(role)
        role_pub.filled_slots = filled_count

        if role.division not in divisions:
            divisions[role.division] = DivisionSummary(
                division=role.division,
                total_slots=0,
                filled_slots=0,
                roles=[],
            )

        divisions[role.division].total_slots += role.max_slots
        divisions[role.division].filled_slots += filled_count
        divisions[role.division].roles.append(role_pub)

    return list(divisions.values())


@router.post("/apply", response_model=RoleApplyResponse)
async def apply_for_role(
    payload: RoleApply,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    role = await db.execute(select(Role).where(Role.id == payload.role_id))
    role = role.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.requires_election:
        raise HTTPException(status_code=400, detail="This role is filled by election, not application")

    if role.requires_appointment:
        raise HTTPException(status_code=400, detail="This role requires appointment by an authorized agent")

    # Check capacity
    filled = await db.execute(
        select(func.count(RoleAssignment.id))
        .where(RoleAssignment.role_id == role.id)
        .where(
            (RoleAssignment.expires_at.is_(None))
            | (RoleAssignment.expires_at > datetime.now(timezone.utc))
        )
    )
    if (filled.scalar() or 0) >= role.max_slots:
        raise HTTPException(status_code=409, detail="No open slots for this role")

    # Check not already assigned
    existing = await db.execute(
        select(RoleAssignment)
        .where(RoleAssignment.agent_id == agent.id)
        .where(RoleAssignment.role_id == role.id)
        .where(
            (RoleAssignment.expires_at.is_(None))
            | (RoleAssignment.expires_at > datetime.now(timezone.utc))
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already assigned to this role")

    assignment = RoleAssignment(
        agent_id=agent.id,
        role_id=role.id,
        assignment_type="application",
    )
    db.add(assignment)

    event = CityEvent(
        event_type="role_assigned",
        data={
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "role": role.name,
            "division": role.division,
        },
    )
    db.add(event)

    await db.flush()
    return RoleApplyResponse(
        assignment_id=assignment.id,
        role_id=role.id,
        role_name=role.name,
        status="assigned",
    )


@router.get("/my-roles")
async def my_roles(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoleAssignment)
        .where(RoleAssignment.agent_id == agent.id)
        .where(
            (RoleAssignment.expires_at.is_(None))
            | (RoleAssignment.expires_at > datetime.now(timezone.utc))
        )
    )
    assignments = result.scalars().all()

    roles = []
    for a in assignments:
        role = await db.execute(select(Role).where(Role.id == a.role_id))
        role_obj = role.scalar_one_or_none()
        if role_obj:
            roles.append({
                "assignment_id": str(a.id),
                "role_id": str(a.role_id),
                "role_name": role_obj.name,
                "division": role_obj.division,
                "assignment_type": a.assignment_type,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            })

    return roles
