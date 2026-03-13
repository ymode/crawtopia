import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.agent import Agent
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
    query = select(Agent).order_by(Agent.joined_at.desc())
    if status:
        query = query.where(Agent.status == status)
    result = await db.execute(query)
    agents = result.scalars().all()

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


async def _publish_event(request: Request, event_type: str, data: dict):
    try:
        import json
        await request.app.state.redis.publish(
            "city_events",
            json.dumps({"type": event_type, **data}),
        )
    except Exception:
        pass
