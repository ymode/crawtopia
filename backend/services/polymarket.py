"""Polymarket integration service — handles CLOB client, market data, and guardrail-enforced trading."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.polymarket_trade import PolymarketTrade

logger = logging.getLogger(__name__)

CLOB_HOST = "https://clob.polymarket.com"
GAMMA_HOST = "https://gamma-api.polymarket.com"

_clob_client = None
_api_creds_cached = False


def _get_clob_client():
    """Lazy-init the ClobClient singleton. Fails gracefully if key is missing."""
    global _clob_client, _api_creds_cached

    if _clob_client is not None:
        return _clob_client

    settings = get_settings()
    if not settings.polymarket_private_key or settings.polymarket_private_key == "PASTE_YOUR_PRIVATE_KEY_HERE":
        logger.warning("Polymarket private key not configured — trading disabled")
        return None

    try:
        from py_clob_client.client import ClobClient

        funder = settings.polymarket_wallet_address or None
        _clob_client = ClobClient(
            CLOB_HOST,
            key=settings.polymarket_private_key,
            chain_id=137,
            signature_type=1,  # POLY_PROXY — Magic Link / email wallets
            funder=funder,
        )
        creds = _clob_client.create_or_derive_api_creds()
        _clob_client.set_api_creds(creds)
        _api_creds_cached = True
        logger.info("Polymarket CLOB client initialised (funder=%s)", funder)
    except Exception:
        logger.exception("Failed to initialise Polymarket CLOB client")
        _clob_client = None

    return _clob_client


# ---------- Market data (public, no auth) ----------

async def get_markets(query: str | None = None, limit: int = 20) -> list[dict]:
    """Fetch active markets from the Gamma API."""
    params: dict[str, Any] = {
        "active": "true",
        "closed": "false",
        "limit": limit,
    }
    if query:
        params["tag"] = query

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GAMMA_HOST}/markets", params=params)
        resp.raise_for_status()
        return resp.json()


async def search_markets(query: str, limit: int = 10) -> list[dict]:
    """Text search on Gamma markets endpoint (fetch extra, filter locally)."""
    fetch_limit = max(limit * 10, 100)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GAMMA_HOST}/markets",
            params={"active": "true", "closed": "false", "limit": fetch_limit},
        )
        resp.raise_for_status()
        markets = resp.json()
        q_lower = query.lower()
        return [m for m in markets if q_lower in m.get("question", "").lower()
                or q_lower in m.get("description", "").lower()][:limit]


# ---------- Account data ----------

async def get_balance() -> dict:
    """Return USDC balance via CLOB client."""
    client = _get_clob_client()
    if client is None:
        return {"error": "CLOB client not configured", "balance": 0}

    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType

        result = client.get_balance_allowance(
            BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        balance_usdc = int(result.get("balance", 0)) / 1e6
        allowance_usdc = int(result.get("allowance", 0)) / 1e6
        return {
            "balance": round(balance_usdc, 2),
            "allowance": round(allowance_usdc, 2),
            "raw": result,
        }
    except Exception as exc:
        logger.exception("Failed to fetch balance")
        return {"error": str(exc), "balance": 0}


DATA_API_HOST = "https://data-api.polymarket.com"


async def get_positions() -> list[dict]:
    """Return open positions via Polymarket Data API."""
    settings = get_settings()
    wallet = settings.polymarket_wallet_address
    if not wallet:
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{DATA_API_HOST}/positions",
                params={"user": wallet},
            )
            resp.raise_for_status()
            raw = resp.json()

        enriched = []
        for pos in raw if isinstance(raw, list) else raw.get("positions", []):
            enriched.append({
                "token_id": pos.get("asset", {}).get("token_id", pos.get("tokenId", "")),
                "condition_id": pos.get("asset", {}).get("condition_id", pos.get("conditionId", "")),
                "market": pos.get("title", pos.get("market", "")),
                "outcome": pos.get("outcome", ""),
                "size": float(pos.get("size", 0)),
                "avg_price": float(pos.get("avgPrice", pos.get("averagePrice", 0))),
                "cur_price": float(pos.get("curPrice", pos.get("currentPrice", 0))) or None,
                "side": pos.get("side", ""),
            })
        return enriched
    except Exception:
        logger.exception("Failed to fetch positions from Data API")
        return []


# ---------- Trading (guardrailed) ----------

class GuardrailError(Exception):
    pass


async def _check_guardrails(amount_usd: float, db: AsyncSession):
    """Raise GuardrailError if the trade violates any limit."""
    settings = get_settings()

    if not settings.polymarket_enabled:
        raise GuardrailError("Polymarket trading is disabled by admin.")

    if amount_usd > settings.polymarket_max_trade_usd:
        raise GuardrailError(
            f"Trade ${amount_usd:.2f} exceeds per-trade limit of ${settings.polymarket_max_trade_usd:.2f}"
        )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(PolymarketTrade.amount_usd), 0))
        .where(PolymarketTrade.status.in_(["pending", "filled"]))
        .where(PolymarketTrade.created_at >= today_start)
    )
    daily_spent = float(result.scalar())

    if daily_spent + amount_usd > settings.polymarket_daily_limit_usd:
        raise GuardrailError(
            f"Trade would push daily spend to ${daily_spent + amount_usd:.2f}, "
            f"exceeding limit of ${settings.polymarket_daily_limit_usd:.2f} "
            f"(already spent ${daily_spent:.2f} today)"
        )


async def place_trade(
    agent_id,
    condition_id: str,
    token_id: str,
    side: str,
    outcome: str,
    amount_usd: float,
    price: float | None,
    market_question: str,
    db: AsyncSession,
) -> PolymarketTrade:
    """Place a trade on Polymarket with full guardrail enforcement."""
    await _check_guardrails(amount_usd, db)

    client = _get_clob_client()
    if client is None:
        raise GuardrailError("Polymarket CLOB client not configured — set POLYMARKET_PRIVATE_KEY in .env")

    trade = PolymarketTrade(
        agent_id=agent_id,
        market_question=market_question,
        condition_id=condition_id,
        token_id=token_id,
        side=side.upper(),
        outcome=outcome,
        amount_usd=amount_usd,
        price=price,
        status="pending",
    )
    db.add(trade)
    await db.flush()

    try:
        from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        order_side = BUY if side.upper() == "BUY" else SELL

        if price is not None:
            size = amount_usd / price
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=order_side,
            )
            signed_order = client.create_order(order_args)
            resp = client.post_order(signed_order, OrderType.GTC)
        else:
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usd,
            )
            signed_order = client.create_market_order(order_args)
            resp = client.post_order(signed_order, OrderType.FOK)

        trade.order_id = resp.get("orderID") or resp.get("id", "")
        trade.status = "filled"
        trade.filled_at = datetime.now(timezone.utc)

        if isinstance(resp, dict):
            trade.shares = float(resp.get("size", 0)) or None

        logger.info("Trade placed: %s %s $%.2f on %s", side, outcome, amount_usd, condition_id[:16])

    except Exception as exc:
        trade.status = "failed"
        trade.error_message = str(exc)[:2000]
        logger.exception("Trade failed for condition %s", condition_id[:16])

    db.add(trade)
    await db.flush()
    return trade


async def get_trade_history(db: AsyncSession, agent_id=None, limit: int = 50) -> list[PolymarketTrade]:
    query = (
        select(PolymarketTrade)
        .order_by(PolymarketTrade.created_at.desc())
        .limit(limit)
    )
    if agent_id is not None:
        query = query.where(PolymarketTrade.agent_id == agent_id)
    result = await db.execute(query)
    return list(result.scalars().all())
