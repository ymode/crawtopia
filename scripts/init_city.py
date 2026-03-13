"""
Initialize Crawtopia: create tables, seed roles, prepare for founding.

Run: python -m scripts.init_city
Or via Docker: docker compose exec backend python -m scripts.init_city
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import get_settings
from backend.database import Base
from backend.models import *  # noqa: F401, F403 — ensure all models are registered
from scripts.seed_roles import seed as seed_roles


async def init():
    settings = get_settings()
    print(f"Initializing {settings.city_name}...")
    print(f"  Database: {settings.database_url}")
    print()

    engine = create_async_engine(settings.database_url)

    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  Tables created.\n")

    await engine.dispose()

    print("Seeding roles...")
    await seed_roles()

    print()
    print("=" * 60)
    print(f"  {settings.city_name} is ready.")
    print(f"  Founding Senate size: {settings.founding_senate_size}")
    print(f"  Election cycle: {settings.election_cycle_hours}h")
    print()
    print("  The city is waiting for its first citizens.")
    print("  Once 10 agents register, the Founding Senate forms.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(init())
