import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Election(Base):
    __tablename__ = "elections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="scheduled", index=True
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nomination_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    voting_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    voting_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    results: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    candidates = relationship("Candidate", back_populates="election", lazy="selectin")
    ballots = relationship("Ballot", back_populates="election")

    def __repr__(self) -> str:
        return f"<Election {self.election_type} cycle={self.cycle_number} ({self.status})>"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    platform: Mapped[str | None] = mapped_column(String(5000))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    election = relationship("Election", back_populates="candidates")
    agent = relationship("Agent")

    __table_args__ = (
        UniqueConstraint("election_id", "agent_id", name="uq_candidate_election_agent"),
    )


class Ballot(Base):
    __tablename__ = "ballots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id"), nullable=False, index=True
    )
    voter_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    rankings: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cast_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    election = relationship("Election", back_populates="ballots")
    voter = relationship("Agent")

    __table_args__ = (
        UniqueConstraint("election_id", "voter_agent_id", name="uq_ballot_election_voter"),
    )
