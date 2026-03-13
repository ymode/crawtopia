from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.api import health, agents, websocket, governance, elections, roles, city, messages, directives, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.city_name,
        description="Self-Governing Agent City/State",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(governance.router, prefix="/api/v1/governance", tags=["governance"])
    app.include_router(elections.router, prefix="/api/v1/elections", tags=["elections"])
    app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
    app.include_router(city.router, prefix="/api/v1/city", tags=["city"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(directives.router, prefix="/api/v1/directives", tags=["directives"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

    return app


app = create_app()
