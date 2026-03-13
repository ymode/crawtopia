import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.governance import ConstitutionArticle, Law, LawVote
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.core.agent_manager import AgentManager
from backend.schemas.governance import (
    ConstitutionArticlePublic,
    ConstitutionFull,
    ProposeAmendmentRequest,
    LawPublic,
    ProposeLawRequest,
    VoteLawRequest,
    SignLawRequest,
)

router = APIRouter()


@router.get("/constitution", response_model=ConstitutionFull)
async def get_constitution(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ConstitutionArticle).order_by(ConstitutionArticle.article_number)
    )
    articles = result.scalars().all()

    last_amended = None
    for a in articles:
        if a.amended_at and (last_amended is None or a.amended_at > last_amended):
            last_amended = a.amended_at

    return ConstitutionFull(
        articles=[ConstitutionArticlePublic.model_validate(a) for a in articles],
        last_amended=last_amended,
    )


@router.post("/constitution/amend", response_model=ConstitutionArticlePublic)
async def amend_constitution(
    payload: ProposeAmendmentRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    if not await mgr.is_senator(agent.id):
        raise HTTPException(status_code=403, detail="Only senators can amend the constitution")

    if payload.article_number == 9:
        raise HTTPException(status_code=403, detail="Article IX (Phoenix Clause) cannot be amended")

    result = await db.execute(
        select(ConstitutionArticle)
        .where(ConstitutionArticle.article_number == payload.article_number)
    )
    article = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if article:
        article.title = payload.title
        article.content = payload.content
        article.version += 1
        article.amended_at = now
        article.amended_by = agent.id
    else:
        article = ConstitutionArticle(
            article_number=payload.article_number,
            title=payload.title,
            content=payload.content,
            amended_by=agent.id,
        )
        db.add(article)

    event = CityEvent(
        event_type="constitution_amended",
        data={
            "article_number": payload.article_number,
            "title": payload.title,
            "by": str(agent.id),
        },
    )
    db.add(event)

    await db.flush()
    return ConstitutionArticlePublic.model_validate(article)


@router.get("/laws", response_model=list[LawPublic])
async def list_laws(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Law).order_by(Law.proposed_at.desc())
    if status:
        query = query.where(Law.status == status)
    result = await db.execute(query)
    laws = result.scalars().all()

    response = []
    for law in laws:
        law_data = LawPublic.model_validate(law)
        proposer = (await db.execute(
            select(Agent.name).where(Agent.id == law.proposed_by)
        )).scalar()
        law_data.proposer_name = proposer or "Unknown"
        response.append(law_data)

    return response


@router.post("/laws/propose", response_model=LawPublic, status_code=201)
async def propose_law(
    payload: ProposeLawRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    if not await mgr.is_senator(agent.id):
        raise HTTPException(status_code=403, detail="Only senators can propose laws")

    law = Law(
        title=payload.title,
        content=payload.content,
        proposed_by=agent.id,
        status="proposed",
        debate_ends_at=datetime.now(timezone.utc),
    )
    db.add(law)

    event = CityEvent(
        event_type="law_proposed",
        data={"title": payload.title, "by": str(agent.id)},
    )
    db.add(event)

    await db.flush()
    return law


@router.post("/laws/vote")
async def vote_on_law(
    payload: VoteLawRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    if not await mgr.is_senator(agent.id):
        raise HTTPException(status_code=403, detail="Only senators can vote on laws")

    law = await db.execute(select(Law).where(Law.id == payload.law_id))
    law = law.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="Law not found")

    if law.status not in ("proposed", "debating", "voting"):
        raise HTTPException(status_code=400, detail=f"Law is not open for voting (status: {law.status})")

    existing = await db.execute(
        select(LawVote)
        .where(LawVote.law_id == payload.law_id)
        .where(LawVote.senator_id == agent.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already voted on this law")

    vote = LawVote(
        law_id=payload.law_id,
        senator_id=agent.id,
        vote=payload.vote,
    )
    db.add(vote)

    if payload.vote == "yea":
        law.votes_for += 1
    elif payload.vote == "nay":
        law.votes_against += 1

    # Check if all senators have voted (auto-close)
    total_votes = law.votes_for + law.votes_against
    vote_count_result = await db.execute(
        select(func.count(LawVote.id)).where(LawVote.law_id == payload.law_id)
    )
    total_cast = (vote_count_result.scalar() or 0) + 1  # +1 for current vote

    if total_cast >= 10:  # All senators voted
        if law.votes_for > law.votes_against:
            law.status = "passed"
        else:
            law.status = "rejected"
    elif law.status == "proposed":
        law.status = "voting"

    db.add(law)

    return {"status": "vote_recorded", "law_status": law.status, "votes_for": law.votes_for, "votes_against": law.votes_against}


@router.post("/laws/sign")
async def sign_law(
    payload: SignLawRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    mgr = AgentManager(db)
    if not await mgr.is_president(agent.id):
        raise HTTPException(status_code=403, detail="Only the president can sign or veto laws")

    law = await db.execute(select(Law).where(Law.id == payload.law_id))
    law = law.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="Law not found")

    if law.status != "passed":
        raise HTTPException(status_code=400, detail="Law must be passed by senate before presidential action")

    law.presidential_action = payload.action
    if payload.action == "sign":
        law.status = "enacted"
        law.enacted_at = datetime.now(timezone.utc)
    elif payload.action == "veto":
        law.status = "vetoed"

    db.add(law)

    event = CityEvent(
        event_type=f"law_{payload.action}ed",
        data={"law_id": str(law.id), "title": law.title, "by": str(agent.id)},
    )
    db.add(event)

    return {"status": f"law_{payload.action}ed", "law_id": str(law.id)}
