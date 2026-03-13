import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    role_name: str | None = Field(
        default=None, description="Target role name (e.g. 'Developer', 'Web Crawler')"
    )
    priority: int = Field(default=0, ge=0, le=10)


class TaskComplete(BaseModel):
    result: str | None = Field(default=None, description="Summary of work done")


class TaskPublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    role_id: uuid.UUID | None
    role_name: str = ""
    assigned_to: uuid.UUID | None
    assignee_name: str = ""
    status: str
    priority: int
    created_by: uuid.UUID
    creator_name: str = ""
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
