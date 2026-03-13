import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RolePublic(BaseModel):
    id: uuid.UUID
    name: str
    division: str
    description: str | None
    max_slots: int
    requires_election: bool
    requires_appointment: bool
    filled_slots: int = 0

    model_config = {"from_attributes": True}


class RoleApply(BaseModel):
    role_id: uuid.UUID
    motivation: str = Field(default="", max_length=2000)


class RoleApplyResponse(BaseModel):
    assignment_id: uuid.UUID
    role_id: uuid.UUID
    role_name: str
    status: str


class DivisionSummary(BaseModel):
    division: str
    total_slots: int
    filled_slots: int
    roles: list[RolePublic]
