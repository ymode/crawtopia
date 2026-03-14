import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    condition_id: str = Field(..., description="Polymarket condition ID")
    token_id: str = Field(..., description="Token ID for the outcome to trade")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="BUY or SELL")
    outcome: str = Field(..., description="Yes or No")
    amount_usd: float = Field(..., gt=0, description="Amount in USD")
    price: float | None = Field(
        default=None, gt=0, le=1, description="Limit price (0-1). Omit for market order."
    )
    market_question: str = Field(
        default="", max_length=1000, description="Market question for display"
    )


class TradePublic(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str = ""
    market_question: str
    condition_id: str
    token_id: str
    side: str
    outcome: str
    amount_usd: float
    price: float | None
    shares: float | None
    order_id: str | None
    status: str
    error_message: str | None
    created_at: datetime
    filled_at: datetime | None

    model_config = {"from_attributes": True}


class MarketPublic(BaseModel):
    condition_id: str
    question: str
    description: str = ""
    outcomes: list[str] = []
    outcome_prices: list[str] = []
    tokens: list[dict] = []
    volume: float = 0
    liquidity: float = 0
    end_date: str = ""
    active: bool = True


class BalancePublic(BaseModel):
    wallet_address: str
    usdc_balance: float
    positions: list[dict] = []
    total_positions: int = 0
