import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="openclaw"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )
    capabilities: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    preferred_roles: Mapped[list | None] = mapped_column(JSONB, default=list)
    auth_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role_assignments = relationship("RoleAssignment", back_populates="agent", lazy="selectin")
    messages_sent = relationship(
        "Message", back_populates="from_agent", foreign_keys="Message.from_agent_id"
    )

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.status})>"
