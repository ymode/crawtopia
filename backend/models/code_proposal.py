import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class CodeProposal(Base):
    __tablename__ = "code_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    files_changed: Mapped[dict | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="open", index=True
    )
    requires_governance: Mapped[bool] = mapped_column(Boolean, default=False)
    governance_approved: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author = relationship("Agent", foreign_keys=[agent_id])
    reviews = relationship("CodeReview", back_populates="proposal", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CodeProposal '{self.title}' ({self.status})>"


class CodeReview(Base):
    __tablename__ = "code_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_proposals.id"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    proposal = relationship("CodeProposal", back_populates="reviews")
    reviewer = relationship("Agent")
