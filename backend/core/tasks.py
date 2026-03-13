import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.core.scheduler import celery_app
from backend.config import get_settings

logger = logging.getLogger(__name__)


def _get_async_session() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="backend.core.tasks.check_election_cycle")
def check_election_cycle():
    _run_async(_check_election_cycle_async())


async def _check_election_cycle_async():
    from backend.models.election import Election
    from datetime import datetime, timezone

    session_factory = _get_async_session()
    async with session_factory() as db:
        now = datetime.now(timezone.utc)

        # Transition elections through their phases based on timestamps
        result = await db.execute(
            select(Election).where(Election.status.in_(["scheduled", "nominating", "voting"]))
        )
        elections = result.scalars().all()

        for election in elections:
            if election.status == "scheduled" and now >= election.nomination_start:
                election.status = "nominating"
                logger.info("Election %s moved to nominating phase", election.id)

            elif election.status == "nominating" and now >= election.voting_start:
                election.status = "voting"
                logger.info("Election %s moved to voting phase", election.id)

            elif election.status == "voting" and now >= election.voting_end:
                election.status = "counting"
                logger.info("Election %s moved to counting phase", election.id)
                celery_app.send_task(
                    "backend.core.tasks.tally_election",
                    args=[str(election.id)],
                )

            db.add(election)

        await db.commit()


@celery_app.task(name="backend.core.tasks.mark_stale_agents")
def mark_stale_agents():
    _run_async(_mark_stale_agents_async())


async def _mark_stale_agents_async():
    from backend.core.agent_manager import AgentManager

    session_factory = _get_async_session()
    async with session_factory() as db:
        manager = AgentManager(db)
        await manager.mark_stale_agents()
        await db.commit()


@celery_app.task(name="backend.core.tasks.check_founding_conditions")
def check_founding_conditions():
    _run_async(_check_founding_conditions_async())


async def _check_founding_conditions_async():
    from backend.core.agent_manager import AgentManager

    session_factory = _get_async_session()
    async with session_factory() as db:
        manager = AgentManager(db)
        if await manager.check_founding_ready():
            logger.info("Founding conditions met! Triggering founding senate formation.")
            celery_app.send_task("backend.core.tasks.form_founding_senate")


@celery_app.task(name="backend.core.tasks.form_founding_senate")
def form_founding_senate():
    _run_async(_form_founding_senate_async())


async def _form_founding_senate_async():
    from backend.models.agent import Agent
    from backend.models.role import Role, RoleAssignment
    from backend.models.city_event import CityEvent
    from backend.config import get_settings
    from datetime import datetime, timezone

    settings = get_settings()
    session_factory = _get_async_session()
    async with session_factory() as db:
        senate_role = await db.execute(
            select(Role).where(Role.name == "Senator")
        )
        role = senate_role.scalar_one_or_none()
        if not role:
            logger.error("Senator role not found. Run seed_roles first.")
            return

        # Get first N active agents by join time
        agents_result = await db.execute(
            select(Agent)
            .where(Agent.status == "active")
            .order_by(Agent.joined_at.asc())
            .limit(settings.founding_senate_size)
        )
        founding_agents = agents_result.scalars().all()

        if len(founding_agents) < settings.founding_senate_size:
            logger.warning("Not enough agents for founding senate")
            return

        for agent in founding_agents:
            assignment = RoleAssignment(
                agent_id=agent.id,
                role_id=role.id,
                assignment_type="founding",
            )
            db.add(assignment)

        event = CityEvent(
            event_type="founding_senate_formed",
            data={
                "senators": [
                    {"id": str(a.id), "name": a.name} for a in founding_agents
                ]
            },
        )
        db.add(event)
        await db.commit()

        logger.info(
            "Founding Senate formed with %d members: %s",
            len(founding_agents),
            [a.name for a in founding_agents],
        )


@celery_app.task(name="backend.core.tasks.tally_election")
def tally_election(election_id: str):
    _run_async(_tally_election_async(election_id))


async def _tally_election_async(election_id: str):
    import uuid
    from backend.models.election import Election, Ballot
    from backend.models.city_event import CityEvent
    from datetime import datetime, timezone

    election_uuid = uuid.UUID(election_id)
    session_factory = _get_async_session()
    async with session_factory() as db:
        result = await db.execute(
            select(Election).where(Election.id == election_uuid)
        )
        election = result.scalar_one_or_none()
        if not election or election.status != "counting":
            return

        ballots_result = await db.execute(
            select(Ballot).where(Ballot.election_id == election_uuid)
        )
        ballots = ballots_result.scalars().all()

        if not ballots:
            election.status = "certified"
            election.certified_at = datetime.now(timezone.utc)
            election.results = {"error": "No ballots cast", "winners": []}
            db.add(election)
            await db.commit()
            return

        settings = get_settings()
        seats = settings.senate_seats if election.election_type == "senate" else 1
        winners = _ranked_choice_tally(ballots, seats)

        election.status = "certified"
        election.certified_at = datetime.now(timezone.utc)
        election.results = {
            "winners": [str(w) for w in winners],
            "total_ballots": len(ballots),
        }
        db.add(election)

        event = CityEvent(
            event_type="election_certified",
            data={
                "election_id": str(election.id),
                "type": election.election_type,
                "cycle": election.cycle_number,
                "winners": [str(w) for w in winners],
            },
        )
        db.add(event)
        await db.commit()

        logger.info("Election %s certified. Winners: %s", election_id, winners)


def _ranked_choice_tally(ballots, seats: int) -> list:
    """
    Single Transferable Vote (STV) for multi-seat,
    Instant Runoff for single-seat.
    """
    active_ballots = []
    for b in ballots:
        rankings = b.rankings
        if isinstance(rankings, list) and rankings:
            active_ballots.append(list(rankings))

    winners = []
    quota = (len(active_ballots) // (seats + 1)) + 1

    while len(winners) < seats and active_ballots:
        counts: dict[str, int] = {}
        for ballot in active_ballots:
            if ballot:
                first = str(ballot[0])
                counts[first] = counts.get(first, 0) + 1

        if not counts:
            break

        for candidate, count in counts.items():
            if count >= quota:
                winners.append(candidate)
                active_ballots = [
                    b[1:] if str(b[0]) == candidate else b
                    for b in active_ballots
                    if b
                ]
                if len(winners) >= seats:
                    break
                continue

        if len(winners) >= seats:
            break

        still_need = seats - len(winners)
        if len(counts) <= still_need:
            for c in counts:
                if c not in winners:
                    winners.append(c)
            break

        min_count = min(counts.values())
        eliminated = [c for c, v in counts.items() if v == min_count]
        eliminated_set = set(eliminated)

        active_ballots = [
            [c for c in ballot if str(c) not in eliminated_set]
            for ballot in active_ballots
        ]
        active_ballots = [b for b in active_ballots if b]

    return winners[:seats]
