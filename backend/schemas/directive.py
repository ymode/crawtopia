import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DirectivePropose(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    priority: int = Field(default=3, ge=1, le=5)
    division: str | None = Field(
        default=None,
        description="Target division (research, finance, engineering, operations, communications)",
    )


class DirectivePublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    priority: int
    status: str
    division: str | None
    proposed_by: uuid.UUID
    proposer_name: str = ""
    approved_by: uuid.UUID | None
    approver_name: str = ""
    created_at: datetime
    approved_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
