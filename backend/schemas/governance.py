import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConstitutionArticlePublic(BaseModel):
    id: uuid.UUID
    article_number: int
    title: str
    content: str
    version: int
    created_at: datetime
    amended_at: datetime | None

    model_config = {"from_attributes": True}


class ConstitutionFull(BaseModel):
    articles: list[ConstitutionArticlePublic]
    last_amended: datetime | None


class ProposeAmendmentRequest(BaseModel):
    article_number: int
    title: str = Field(..., max_length=500)
    content: str


class LawPublic(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    proposed_by: uuid.UUID
    proposer_name: str = ""
    status: str
    proposed_at: datetime
    debate_ends_at: datetime | None
    votes_for: int
    votes_against: int
    presidential_action: str | None
    enacted_at: datetime | None

    model_config = {"from_attributes": True}


class ProposeLawRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class VoteLawRequest(BaseModel):
    law_id: uuid.UUID
    vote: str = Field(..., pattern="^(yea|nay|abstain)$")


class SignLawRequest(BaseModel):
    law_id: uuid.UUID
    action: str = Field(..., pattern="^(sign|veto)$")
