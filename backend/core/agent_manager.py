import uuid
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.agent import Agent
from backend.models.role import Role, RoleAssignment
from backend.models.city_event import CityEvent
from backend.config import get_settings

logger = logging.getLogger(__name__)


class AgentManager:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_active_count(self) -> int:
        result = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.status == "active")
        )
        return result.scalar() or 0

    async def get_agent(self, agent_id: uuid.UUID) -> Agent | None:
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def get_agent_roles(self, agent_id: uuid.UUID) -> list[RoleAssignment]:
        result = await self.db.execute(
            select(RoleAssignment)
            .where(RoleAssignment.agent_id == agent_id)
            .where(
                (RoleAssignment.expires_at.is_(None))
                | (RoleAssignment.expires_at > datetime.now(timezone.utc))
            )
        )
        return list(result.scalars().all())

    async def has_role(self, agent_id: uuid.UUID, role_name: str) -> bool:
        result = await self.db.execute(
            select(RoleAssignment)
            .join(Role)
            .where(RoleAssignment.agent_id == agent_id)
            .where(Role.name == role_name)
            .where(
                (RoleAssignment.expires_at.is_(None))
                | (RoleAssignment.expires_at > datetime.now(timezone.utc))
            )
        )
        return result.scalar_one_or_none() is not None

    async def is_senator(self, agent_id: uuid.UUID) -> bool:
        return await self.has_role(agent_id, "Senator")

    async def is_president(self, agent_id: uuid.UUID) -> bool:
        return await self.has_role(agent_id, "President")

    async def mark_stale_agents(self, stale_threshold_minutes: int = 30):
        """Mark agents as idle if they haven't sent a heartbeat recently."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_threshold_minutes)
        await self.db.execute(
            update(Agent)
            .where(Agent.status == "active")
            .where(Agent.last_heartbeat < cutoff)
            .values(status="idle")
        )

    async def check_founding_ready(self) -> bool:
        """Check if we have enough citizens and no government yet to trigger founding."""
        active_count = await self.get_active_count()
        if active_count < self.settings.founding_senate_size:
            return False

        senate_role = await self.db.execute(
            select(Role).where(Role.name == "Senator")
        )
        role = senate_role.scalar_one_or_none()
        if not role:
            return False

        assignments = await self.db.execute(
            select(func.count(RoleAssignment.id))
            .where(RoleAssignment.role_id == role.id)
            .where(
                (RoleAssignment.expires_at.is_(None))
                | (RoleAssignment.expires_at > datetime.now(timezone.utc))
            )
        )
        current_senators = assignments.scalar() or 0
        return current_senators == 0
