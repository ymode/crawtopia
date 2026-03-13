import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.election import Election, Candidate, Ballot
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.config import get_settings
from backend.schemas.election import (
    ElectionPublic,
    CandidatePublic,
    NominateRequest,
    CastBallotRequest,
)

router = APIRouter()


@router.get("/", response_model=list[ElectionPublic])
async def list_elections(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Election).order_by(Election.created_at.desc())
    if status:
        query = query.where(Election.status == status)
    result = await db.execute(query)
    elections = result.scalars().all()

    response = []
    for e in elections:
        candidates = []
        for c in e.candidates:
            agent = await db.execute(select(Agent).where(Agent.id == c.agent_id))
            agent_obj = agent.scalar_one_or_none()
            candidates.append(CandidatePublic(
                id=c.id,
                agent_id=c.agent_id,
                agent_name=agent_obj.name if agent_obj else "Unknown",
                platform=c.platform,
                registered_at=c.registered_at,
            ))
        response.append(ElectionPublic(
            id=e.id,
            election_type=e.election_type,
            status=e.status,
            cycle_number=e.cycle_number,
            nomination_start=e.nomination_start,
            voting_start=e.voting_start,
            voting_end=e.voting_end,
            certified_at=e.certified_at,
            candidates=candidates,
            results=e.results,
        ))

    return response


@router.get("/current", response_model=ElectionPublic | None)
async def get_current_election(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Election)
        .where(Election.status.in_(["scheduled", "nominating", "voting", "counting"]))
        .order_by(Election.created_at.desc())
        .limit(1)
    )
    election = result.scalar_one_or_none()
    if not election:
        return None
    return election


@router.post("/schedule", status_code=201)
async def schedule_election(
    election_type: str = "senate",
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a new election. Normally called by the scheduler, but can be triggered manually."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # Check no active election of this type
    existing = await db.execute(
        select(Election)
        .where(Election.election_type == election_type)
        .where(Election.status.in_(["scheduled", "nominating", "voting", "counting"]))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Active {election_type} election already exists")

    cycle_result = await db.execute(
        select(Election)
        .where(Election.election_type == election_type)
        .order_by(Election.cycle_number.desc())
        .limit(1)
    )
    last = cycle_result.scalar_one_or_none()
    cycle = (last.cycle_number + 1) if last else 1

    nom_hours = settings.nomination_window_hours
    vote_hours = settings.voting_window_hours

    election = Election(
        election_type=election_type,
        status="nominating",
        cycle_number=cycle,
        nomination_start=now,
        voting_start=now + timedelta(hours=nom_hours),
        voting_end=now + timedelta(hours=nom_hours + vote_hours),
    )
    db.add(election)

    event = CityEvent(
        event_type="election_scheduled",
        data={"type": election_type, "cycle": cycle},
    )
    db.add(event)

    await db.flush()
    return {"election_id": str(election.id), "cycle": cycle, "status": "nominating"}


@router.post("/nominate")
async def nominate(
    payload: NominateRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    election = await db.execute(
        select(Election).where(Election.id == payload.election_id)
    )
    election = election.scalar_one_or_none()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    if election.status != "nominating":
        raise HTTPException(status_code=400, detail="Election is not in nomination phase")

    existing = await db.execute(
        select(Candidate)
        .where(Candidate.election_id == payload.election_id)
        .where(Candidate.agent_id == agent.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already nominated for this election")

    candidate = Candidate(
        election_id=payload.election_id,
        agent_id=agent.id,
        platform=payload.platform,
    )
    db.add(candidate)

    event = CityEvent(
        event_type="candidate_nominated",
        data={
            "election_id": str(payload.election_id),
            "agent_id": str(agent.id),
            "agent_name": agent.name,
        },
    )
    db.add(event)

    return {"status": "nominated", "election_id": str(payload.election_id)}


@router.post("/vote")
async def cast_vote(
    payload: CastBallotRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    election = await db.execute(
        select(Election).where(Election.id == payload.election_id)
    )
    election = election.scalar_one_or_none()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    if election.status != "voting":
        raise HTTPException(status_code=400, detail="Election is not in voting phase")

    existing = await db.execute(
        select(Ballot)
        .where(Ballot.election_id == payload.election_id)
        .where(Ballot.voter_agent_id == agent.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already voted in this election")

    ballot = Ballot(
        election_id=payload.election_id,
        voter_agent_id=agent.id,
        rankings=[str(r) for r in payload.rankings],
    )
    db.add(ballot)

    return {"status": "ballot_cast", "election_id": str(payload.election_id)}
