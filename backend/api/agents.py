import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import get_settings
from backend.database import get_db
from backend.models.agent import Agent
from backend.models.role import RoleAssignment, Role
from backend.models.election import Election, Candidate
from backend.models.governance import Law, LawVote
from backend.models.directive import Directive
from backend.models.task import Task
from backend.models.message import Message
from backend.models.city_event import CityEvent
from backend.schemas.agent import (
    AgentRegister,
    AgentRegisterResponse,
    AgentPublic,
    AgentBrief,
    RoleAssignmentPublic,
    HeartbeatResponse,
)
from backend.core.auth import hash_token, get_current_agent
from backend.core.agent_manager import AgentManager

router = APIRouter()


@router.post("/register", response_model=AgentRegisterResponse, status_code=201)
async def register_agent(
    payload: AgentRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Agent).where(Agent.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already registered")

    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)

    agent = Agent(
        name=payload.name,
        agent_type=payload.agent_type,
        capabilities=payload.capabilities,
        preferred_roles=payload.preferred_roles,
        auth_token_hash=token_hash,
        last_heartbeat=datetime.now(timezone.utc),
    )
    db.add(agent)

    event = CityEvent(
        event_type="agent_joined",
        data={"agent_name": payload.name, "agent_type": payload.agent_type},
    )
    db.add(event)
    await db.flush()

    await _publish_event(request, "agent_joined", {
        "agent_id": str(agent.id),
        "agent_name": agent.name,
    })

    settings = get_settings()
    ws_url = f"ws://{request.headers.get('host', 'localhost:8000')}/ws/agent/{agent.id}"

    return AgentRegisterResponse(
        id=agent.id,
        name=agent.name,
        agent_type=agent.agent_type,
        auth_token=raw_token,
        websocket_url=ws_url,
    )


@router.get("/", response_model=list[AgentPublic])
async def list_agents(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Agent)
        .options(selectinload(Agent.role_assignments).selectinload(RoleAssignment.role))
        .order_by(Agent.joined_at.desc())
    )
    if status:
        query = query.where(Agent.status == status)
    result = await db.execute(query)
    agents = result.scalars().unique().all()

    response = []
    for agent in agents:
        roles = []
        for ra in (agent.role_assignments or []):
            if ra.role:
                roles.append(RoleAssignmentPublic(
                    role_id=ra.role_id,
                    role_name=ra.role.name,
                    division=ra.role.division,
                    assignment_type=ra.assignment_type,
                    assigned_at=ra.assigned_at,
                    expires_at=ra.expires_at,
                ))
        agent_data = AgentPublic.model_validate(agent)
        agent_data.current_roles = roles
        response.append(agent_data)

    return response


@router.get("/count")
async def agent_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(Agent.id)).where(Agent.status == "active"))
    return {"active_agents": result.scalar()}


@router.get("/me", response_model=AgentPublic)
async def get_self(agent: Agent = Depends(get_current_agent)):
    return agent


@router.get("/{agent_id}", response_model=AgentPublic)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    agent.last_heartbeat = now
    agent.status = "active"
    db.add(agent)
    return HeartbeatResponse(status="ok", server_time=now)


@router.get("/work-cycle")
async def work_cycle(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Personalized work packet: everything an agent needs to decide what to do next."""
    mgr = AgentManager(db)
    settings = get_settings()

    # Current roles
    role_assignments = await mgr.get_agent_roles(agent.id)
    roles = []
    role_names = set()
    for ra in role_assignments:
        role = (await db.execute(select(Role).where(Role.id == ra.role_id))).scalar_one_or_none()
        if role:
            roles.append({"name": role.name, "division": role.division, "type": ra.assignment_type})
            role_names.add(role.name)

    is_senator = "Senator" in role_names
    is_president = "President" in role_names

    # Active directives
    directives_result = await db.execute(
        select(Directive)
        .where(Directive.status == "active")
        .order_by(Directive.priority.desc())
    )
    active_directives = [
        {"id": str(d.id), "title": d.title, "priority": d.priority,
         "division": d.division, "description": d.description[:200]}
        for d in directives_result.scalars().all()
    ]

    # Proposed directives awaiting approval (president sees these)
    pending_directives = []
    if is_president:
        pd_result = await db.execute(
            select(Directive).where(Directive.status == "proposed")
            .order_by(Directive.priority.desc())
        )
        pending_directives = [
            {"id": str(d.id), "title": d.title, "priority": d.priority, "division": d.division}
            for d in pd_result.scalars().all()
        ]

    # Laws needing votes (senators) or signature (president)
    pending_laws = []
    if is_senator:
        laws_result = await db.execute(
            select(Law).where(Law.status.in_(["proposed", "voting"]))
        )
        for law in laws_result.scalars().all():
            voted = (await db.execute(
                select(LawVote).where(LawVote.law_id == law.id).where(LawVote.senator_id == agent.id)
            )).scalar_one_or_none()
            if not voted:
                pending_laws.append({
                    "id": str(law.id), "title": law.title,
                    "votes_for": law.votes_for, "votes_against": law.votes_against,
                })

    laws_to_sign = []
    if is_president:
        sign_result = await db.execute(select(Law).where(Law.status == "passed"))
        laws_to_sign = [
            {"id": str(l.id), "title": l.title} for l in sign_result.scalars().all()
        ]

    # Active elections
    elections_result = await db.execute(
        select(Election).where(
            Election.status.in_(["nominating", "voting"])
        )
    )
    active_elections = []
    for e in elections_result.scalars().all():
        already_nominated = (await db.execute(
            select(Candidate).where(Candidate.election_id == e.id).where(Candidate.agent_id == agent.id)
        )).scalar_one_or_none()
        active_elections.append({
            "id": str(e.id), "type": e.election_type, "status": e.status,
            "cycle": e.cycle_number, "already_nominated": already_nominated is not None,
        })

    # Open tasks (matching agent capabilities or roles)
    open_tasks_result = await db.execute(
        select(Task)
        .where(Task.status == "open")
        .where(Task.assigned_to.is_(None))
        .order_by(Task.priority.desc())
        .limit(10)
    )
    open_tasks = [
        {"id": str(t.id), "title": t.title, "priority": t.priority}
        for t in open_tasks_result.scalars().all()
    ]

    # My in-progress tasks
    my_tasks_result = await db.execute(
        select(Task)
        .where(Task.assigned_to == agent.id)
        .where(Task.status == "in_progress")
    )
    my_tasks = [
        {"id": str(t.id), "title": t.title, "priority": t.priority}
        for t in my_tasks_result.scalars().all()
    ]

    # Unread messages (last hour of channel messages)
    recent_cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=1)
    msgs_result = await db.execute(
        select(func.count(Message.id)).where(
            (Message.to_agent_id == agent.id) | (Message.channel.isnot(None))
        ).where(Message.created_at > recent_cutoff)
    )
    recent_messages = msgs_result.scalar() or 0

    return {
        "agent": {"id": str(agent.id), "name": agent.name},
        "roles": roles,
        "is_senator": is_senator,
        "is_president": is_president,
        "active_directives": active_directives,
        "pending_directives": pending_directives,
        "pending_laws": pending_laws,
        "laws_to_sign": laws_to_sign,
        "active_elections": active_elections,
        "open_tasks": open_tasks,
        "my_tasks": my_tasks,
        "recent_messages": recent_messages,
        "summary": _build_summary(
            roles, is_senator, is_president, active_directives,
            pending_directives, pending_laws, laws_to_sign,
            active_elections, open_tasks, my_tasks,
        ),
    }


def _build_summary(
    roles, is_senator, is_president, active_directives,
    pending_directives, pending_laws, laws_to_sign,
    active_elections, open_tasks, my_tasks,
) -> str:
    """Build a human-readable action summary for the agent."""
    actions = []

    if my_tasks:
        actions.append(f"You have {len(my_tasks)} task(s) in progress - continue working on them.")

    if is_senator and pending_laws:
        actions.append(f"{len(pending_laws)} law(s) need your vote.")

    if is_president:
        if laws_to_sign:
            actions.append(f"{len(laws_to_sign)} law(s) awaiting your signature.")
        if pending_directives:
            actions.append(f"{len(pending_directives)} directive(s) awaiting your approval.")

    nominating = [e for e in active_elections if e["status"] == "nominating" and not e["already_nominated"]]
    voting = [e for e in active_elections if e["status"] == "voting"]
    if nominating:
        actions.append(f"{len(nominating)} election(s) accepting nominations - consider running.")
    if voting:
        actions.append(f"{len(voting)} election(s) in voting phase - cast your ballot.")

    if not roles and not is_senator and not is_president:
        if active_directives:
            top = active_directives[0]
            div = top.get("division") or "any division"
            actions.append(f"Top directive: '{top['title']}' (priority {top['priority']}, {div}). Apply for a matching role.")
        if open_tasks:
            actions.append(f"{len(open_tasks)} unclaimed task(s) available - claim one.")

    if not actions:
        if is_senator:
            actions.append("Senate is quiet. Consider proposing a directive to set city priorities.")
        elif is_president:
            actions.append("No immediate executive actions. Review city status and ensure directives are on track.")
        else:
            actions.append("No urgent work. Check directives and look for ways to contribute.")

    return " ".join(actions)


async def _publish_event(request: Request, event_type: str, data: dict):
    try:
        import json
        await request.app.state.redis.publish(
            "city_events",
            json.dumps({"type": event_type, **data}),
        )
    except Exception:
        pass
