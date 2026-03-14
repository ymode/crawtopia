"""Polymarket prediction market API — browse markets, check balance, and trade."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.config import get_settings
from backend.models.agent import Agent
from backend.models.polymarket_trade import PolymarketTrade
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.schemas.polymarket import (
    TradeRequest,
    TradePublic,
    MarketPublic,
    BalancePublic,
)
from backend.services import polymarket as pm_service

router = APIRouter()


async def _enrich_trade(trade: PolymarketTrade, db: AsyncSession) -> TradePublic:
    data = TradePublic.model_validate(trade)
    agent = (await db.execute(
        select(Agent.name).where(Agent.id == trade.agent_id)
    )).scalar()
    data.agent_name = agent or "Unknown"
    return data


@router.get("/markets", response_model=list[MarketPublic])
async def list_markets(
    query: str | None = Query(default=None, description="Search term or tag"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Browse active Polymarket prediction markets."""
    if query:
        events = await pm_service.search_markets(query, limit=limit)
        markets = []
        for ev in events:
            for m in ev.get("markets", [ev]):
                markets.append(_gamma_to_market(m))
        return markets[:limit]

    raw = await pm_service.get_markets(limit=limit)
    return [_gamma_to_market(m) for m in raw]


@router.get("/balance", response_model=BalancePublic)
async def get_balance():
    """Check the Polymarket USDC balance."""
    settings = get_settings()
    balance_data = await pm_service.get_balance()
    positions = await pm_service.get_positions()
    return BalancePublic(
        wallet_address=settings.polymarket_wallet_address,
        usdc_balance=balance_data.get("balance", 0),
        positions=positions,
        total_positions=len(positions),
    )


@router.get("/positions")
async def get_positions():
    """List current Polymarket positions with token details."""
    return await pm_service.get_positions()


@router.post("/trade", response_model=TradePublic, status_code=201)
async def place_trade(
    payload: TradeRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Place a trade on Polymarket (guardrails enforced server-side)."""
    try:
        trade = await pm_service.place_trade(
            agent_id=agent.id,
            condition_id=payload.condition_id,
            token_id=payload.token_id,
            side=payload.side,
            outcome=payload.outcome,
            amount_usd=payload.amount_usd,
            price=payload.price,
            market_question=payload.market_question,
            db=db,
        )
    except pm_service.GuardrailError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    event = CityEvent(
        event_type="polymarket_trade",
        data={
            "trade_id": str(trade.id),
            "agent": str(agent.id),
            "agent_name": agent.name,
            "side": trade.side,
            "outcome": trade.outcome,
            "amount_usd": trade.amount_usd,
            "market": trade.market_question[:200],
            "status": trade.status,
        },
    )
    db.add(event)
    await db.flush()

    return await _enrich_trade(trade, db)


@router.get("/trades", response_model=list[TradePublic])
async def trade_history(
    agent_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List trade history."""
    import uuid as _uuid
    aid = _uuid.UUID(agent_id) if agent_id else None
    trades = await pm_service.get_trade_history(db, agent_id=aid, limit=limit)
    return [await _enrich_trade(t, db) for t in trades]


@router.get("/guardrails")
async def get_guardrails(db: AsyncSession = Depends(get_db)):
    """Return current guardrail settings and today's spend."""
    from datetime import datetime, timezone
    from sqlalchemy import func

    settings = get_settings()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(PolymarketTrade.amount_usd), 0))
        .where(PolymarketTrade.status.in_(["pending", "filled"]))
        .where(PolymarketTrade.created_at >= today_start)
    )
    daily_spent = float(result.scalar())

    return {
        "enabled": settings.polymarket_enabled,
        "max_trade_usd": settings.polymarket_max_trade_usd,
        "daily_limit_usd": settings.polymarket_daily_limit_usd,
        "daily_spent_usd": round(daily_spent, 2),
        "daily_remaining_usd": round(settings.polymarket_daily_limit_usd - daily_spent, 2),
    }


def _gamma_to_market(raw: dict) -> MarketPublic:
    """Convert Gamma API market object to our schema."""
    import json as _json

    tokens = []
    for t in raw.get("tokens", []):
        tokens.append({
            "token_id": t.get("token_id", ""),
            "outcome": t.get("outcome", ""),
            "price": t.get("price", ""),
        })

    outcomes = raw.get("outcomes", [])
    if isinstance(outcomes, str):
        try:
            outcomes = _json.loads(outcomes)
        except (ValueError, TypeError):
            outcomes = []

    outcome_prices = raw.get("outcomePrices", [])
    if isinstance(outcome_prices, str):
        try:
            outcome_prices = _json.loads(outcome_prices)
        except (ValueError, TypeError):
            outcome_prices = []

    clob_token_ids = raw.get("clobTokenIds", "")
    if isinstance(clob_token_ids, str):
        try:
            clob_ids = _json.loads(clob_token_ids)
        except (ValueError, TypeError):
            clob_ids = []
    else:
        clob_ids = clob_token_ids or []

    if not tokens and clob_ids and outcomes:
        for i, cid in enumerate(clob_ids):
            tokens.append({
                "token_id": cid,
                "outcome": outcomes[i] if i < len(outcomes) else f"Outcome {i}",
                "price": outcome_prices[i] if i < len(outcome_prices) else "",
            })

    return MarketPublic(
        condition_id=raw.get("condition_id", raw.get("conditionId", "")),
        question=raw.get("question", raw.get("title", "")),
        description=raw.get("description", "")[:500],
        outcomes=outcomes,
        outcome_prices=outcome_prices,
        tokens=tokens,
        volume=float(raw.get("volume", 0) or 0),
        liquidity=float(raw.get("liquidity", 0) or 0),
        end_date=raw.get("end_date_iso", raw.get("endDate", raw.get("endDateIso", ""))),
        active=raw.get("active", True),
    )
