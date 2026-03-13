import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.message import Message
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.schemas.message import SendMessageRequest, MessagePublic

router = APIRouter()


@router.post("/send", response_model=MessagePublic, status_code=201)
async def send_message(
    payload: SendMessageRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    if not payload.to_agent_id and not payload.channel:
        raise HTTPException(status_code=400, detail="Specify to_agent_id or channel")

    msg = Message(
        from_agent_id=agent.id,
        to_agent_id=payload.to_agent_id,
        channel=payload.channel,
        content=payload.content,
        message_type=payload.message_type,
    )
    db.add(msg)
    await db.flush()

    return MessagePublic(
        id=msg.id,
        from_agent_id=msg.from_agent_id,
        from_agent_name=agent.name,
        to_agent_id=msg.to_agent_id,
        channel=msg.channel,
        content=msg.content,
        message_type=msg.message_type,
        created_at=msg.created_at,
    )


@router.get("/channel/{channel}", response_model=list[MessagePublic])
async def get_channel_messages(
    channel: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.channel == channel)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    response = []
    for m in messages:
        sender = await db.execute(select(Agent).where(Agent.id == m.from_agent_id))
        sender_obj = sender.scalar_one_or_none()
        response.append(MessagePublic(
            id=m.id,
            from_agent_id=m.from_agent_id,
            from_agent_name=sender_obj.name if sender_obj else "Unknown",
            to_agent_id=m.to_agent_id,
            channel=m.channel,
            content=m.content,
            message_type=m.message_type,
            created_at=m.created_at,
        ))

    return response
