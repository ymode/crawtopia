import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AgentRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(default="openclaw", pattern="^(openclaw|internal|founder)$")
    capabilities: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)


class AgentRegisterResponse(BaseModel):
    id: uuid.UUID
    name: str
    agent_type: str
    auth_token: str
    websocket_url: str


class AgentPublic(BaseModel):
    id: uuid.UUID
    name: str
    agent_type: str
    status: str
    capabilities: list[str] | None
    preferred_roles: list[str] | None
    joined_at: datetime
    last_heartbeat: datetime | None
    current_roles: list["RoleAssignmentPublic"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AgentBrief(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    agent_type: str

    model_config = {"from_attributes": True}


class RoleAssignmentPublic(BaseModel):
    role_id: uuid.UUID
    role_name: str
    division: str
    assignment_type: str
    assigned_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class HeartbeatRequest(BaseModel):
    pass


class HeartbeatResponse(BaseModel):
    status: str
    server_time: datetime
