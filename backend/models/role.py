import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    division: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(2000))
    max_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    requires_election: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_appointment: Mapped[bool] = mapped_column(Boolean, default=False)
    required_capabilities: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    assignments = relationship("RoleAssignment", back_populates="role", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Role {self.name} [{self.division}]>"


class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True
    )
    assignment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="application"
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent = relationship("Agent", back_populates="role_assignments", foreign_keys=[agent_id])
    role = relationship("Role", back_populates="assignments")

    def __repr__(self) -> str:
        return f"<RoleAssignment agent={self.agent_id} role={self.role_id}>"
