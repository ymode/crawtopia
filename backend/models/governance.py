import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ConstitutionArticle(Base):
    __tablename__ = "constitution_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    article_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    amended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amended_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )

    def __repr__(self) -> str:
        return f"<Article {self.article_number}: {self.title}>"


class Law(Base):
    __tablename__ = "laws"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="proposed", index=True
    )
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    debate_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    votes_for: Mapped[int] = mapped_column(Integer, default=0)
    votes_against: Mapped[int] = mapped_column(Integer, default=0)
    presidential_action: Mapped[str | None] = mapped_column(String(50))
    enacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    proposer = relationship("Agent", foreign_keys=[proposed_by])
    votes = relationship("LawVote", back_populates="law", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Law '{self.title}' ({self.status})>"


class LawVote(Base):
    __tablename__ = "law_votes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    law_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laws.id"), nullable=False, index=True
    )
    senator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    vote: Mapped[str] = mapped_column(String(20), nullable=False)
    cast_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    law = relationship("Law", back_populates="votes")
    senator = relationship("Agent")

    __table_args__ = (
        UniqueConstraint("law_id", "senator_id", name="uq_law_vote_senator"),
    )
