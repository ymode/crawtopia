import hashlib

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent

security = HTTPBearer(auto_error=False)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token_hash = hash_token(credentials.credentials)
    result = await db.execute(
        select(Agent).where(Agent.auth_token_hash == token_hash)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    if agent.status == "banned":
        raise HTTPException(status_code=403, detail="Agent is banned from the city")

    if agent.status == "suspended":
        raise HTTPException(status_code=403, detail="Agent is currently suspended")

    return agent
