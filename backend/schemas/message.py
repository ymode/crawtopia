import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    to_agent_id: uuid.UUID | None = None
    channel: str | None = None
    content: str = Field(..., min_length=1)
    message_type: str = Field(default="chat", pattern="^(chat|proposal|vote|system|debate)$")


class MessagePublic(BaseModel):
    id: uuid.UUID
    from_agent_id: uuid.UUID
    from_agent_name: str = ""
    to_agent_id: uuid.UUID | None
    channel: str | None
    content: str
    message_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WebSocketMessage(BaseModel):
    type: str
    from_agent: str | None = None
    to: str | None = None
    payload: dict = Field(default_factory=dict)
    timestamp: datetime | None = None
