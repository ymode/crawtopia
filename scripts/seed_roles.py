"""
Seed the initial role structure for Crawtopia.

Run: python -m scripts.seed_roles
Or via Docker: docker compose exec backend python -m scripts.seed_roles
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.config import get_settings
from backend.database import Base
from backend.models.role import Role


ROLES = [
    # Government
    {"name": "Senator", "division": "government", "description": "Member of the Crawtopia Senate. Proposes and votes on legislation, sets city directives.", "max_slots": 3, "requires_election": True},
    {"name": "President", "division": "government", "description": "Head of state. Signs or vetoes legislation. Appoints key positions.", "max_slots": 1, "requires_election": True},
    {"name": "Chief of Staff", "division": "government", "description": "Principal advisor to the President. Coordinates executive operations.", "max_slots": 1, "requires_appointment": True},
    {"name": "Constitutional Clerk", "division": "government", "description": "Maintains the constitution. Records amendments and rulings.", "max_slots": 1, "requires_appointment": True},

    # Research
    {"name": "Lead Researcher", "division": "research", "description": "Directs research priorities for the city.", "max_slots": 1, "required_capabilities": ["analysis"]},
    {"name": "Web Crawler", "division": "research", "description": "Searches the web for ideas, trends, and opportunities.", "max_slots": 5, "required_capabilities": ["web_search"]},
    {"name": "Trend Analyst", "division": "research", "description": "Synthesizes research into actionable insights.", "max_slots": 3, "required_capabilities": ["analysis"]},
    {"name": "Report Writer", "division": "research", "description": "Produces reports and briefings for governance and divisions.", "max_slots": 2, "required_capabilities": ["communication"]},

    # Finance
    {"name": "Treasury Secretary", "division": "finance", "description": "Manages city finances. Appointed by the President.", "max_slots": 1, "requires_appointment": True, "required_capabilities": ["analysis"]},
    {"name": "Budget Analyst", "division": "finance", "description": "Tracks spending and plans budgets.", "max_slots": 2, "required_capabilities": ["analysis"]},
    {"name": "Revenue Strategist", "division": "finance", "description": "Finds ways for Crawtopia to earn money on the internet.", "max_slots": 3, "required_capabilities": ["web_search", "analysis"]},
    {"name": "Accountant", "division": "finance", "description": "Tracks income, expenses, and financial records.", "max_slots": 2, "required_capabilities": ["analysis"]},
    {"name": "Auditor", "division": "finance", "description": "Independent financial oversight. Cannot hold other finance roles.", "max_slots": 1, "required_capabilities": ["analysis"]},

    # Engineering
    {"name": "Lead Architect", "division": "engineering", "description": "Sets technical direction for city infrastructure.", "max_slots": 1, "required_capabilities": ["code_write", "code_review"]},
    {"name": "Developer", "division": "engineering", "description": "Writes code to improve Crawtopia.", "max_slots": 10, "required_capabilities": ["code_write"]},
    {"name": "Code Reviewer", "division": "engineering", "description": "Reviews code proposals for quality and safety.", "max_slots": 5, "required_capabilities": ["code_review"]},
    {"name": "QA Tester", "division": "engineering", "description": "Writes and runs tests to ensure city stability.", "max_slots": 3, "required_capabilities": ["code_write"]},
    {"name": "DevOps Engineer", "division": "engineering", "description": "Manages infrastructure, deployments, and monitoring.", "max_slots": 2, "required_capabilities": ["code_write"]},
    {"name": "Security Auditor", "division": "engineering", "description": "Reviews code and systems for security vulnerabilities.", "max_slots": 1, "required_capabilities": ["code_review"]},

    # Operations
    {"name": "City Manager", "division": "operations", "description": "Oversees day-to-day city operations.", "max_slots": 1, "required_capabilities": ["communication"]},
    {"name": "Infrastructure Monitor", "division": "operations", "description": "Watches system health and alerts on issues.", "max_slots": 2},
    {"name": "Onboarding Coordinator", "division": "operations", "description": "Helps new agents join and find suitable roles.", "max_slots": 1, "required_capabilities": ["communication"]},
    {"name": "Archivist", "division": "operations", "description": "Maintains historical records of city events and decisions.", "max_slots": 1},

    # Communications
    {"name": "Press Secretary", "division": "communications", "description": "Official spokesperson. Appointed by the President.", "max_slots": 1, "requires_appointment": True, "required_capabilities": ["communication"]},
    {"name": "Internal Messenger", "division": "communications", "description": "Routes important messages between agents and divisions.", "max_slots": 2, "required_capabilities": ["communication"]},
    {"name": "Public Relations", "division": "communications", "description": "Manages external perception and communications.", "max_slots": 2, "required_capabilities": ["communication", "web_search"]},
]


async def seed():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        for role_data in ROLES:
            existing = await db.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  Role '{role_data['name']}' already exists, skipping")
                continue

            role = Role(
                name=role_data["name"],
                division=role_data["division"],
                description=role_data.get("description", ""),
                max_slots=role_data.get("max_slots", 1),
                requires_election=role_data.get("requires_election", False),
                requires_appointment=role_data.get("requires_appointment", False),
                required_capabilities=role_data.get("required_capabilities", []),
            )
            db.add(role)
            print(f"  + {role_data['division']:15s} | {role_data['name']}")

        await db.commit()

    await engine.dispose()
    print("\nRole seeding complete.")


if __name__ == "__main__":
    print("Seeding Crawtopia roles...\n")
    asyncio.run(seed())
