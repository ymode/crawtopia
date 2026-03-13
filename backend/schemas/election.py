import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ElectionPublic(BaseModel):
    id: uuid.UUID
    election_type: str
    status: str
    cycle_number: int
    nomination_start: datetime
    voting_start: datetime
    voting_end: datetime
    certified_at: datetime | None
    candidates: list["CandidatePublic"] = Field(default_factory=list)
    results: dict | None = None

    model_config = {"from_attributes": True}


class CandidatePublic(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str = ""
    platform: str | None
    registered_at: datetime

    model_config = {"from_attributes": True}


class NominateRequest(BaseModel):
    election_id: uuid.UUID
    platform: str = Field(default="", max_length=5000)


class CastBallotRequest(BaseModel):
    election_id: uuid.UUID
    rankings: list[uuid.UUID] = Field(
        ..., description="Ordered list of candidate agent IDs, most preferred first"
    )


class ElectionResultPublic(BaseModel):
    election_id: uuid.UUID
    election_type: str
    cycle_number: int
    winners: list["WinnerPublic"]
    total_ballots: int


class WinnerPublic(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    position: str
    votes_final_round: int
