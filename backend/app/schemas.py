from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="Trader", min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    role: str
    virtual_cash_balance: float
    created_at: datetime


class TradeIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    shares: int = Field(gt=0, le=1_000_000)


class TradeOut(BaseModel):
    transaction_id: int
    symbol: str
    type: str
    shares: int
    price: float
    total: float
    realized_pnl: float
    cash_balance: float


class QuoteOut(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    day_high: float
    day_low: float
    cached: bool = False


class HoldingOut(BaseModel):
    symbol: str
    quantity: int
    avg_buy_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PortfolioOut(BaseModel):
    cash: float
    holdings_value: float
    net_worth: float
    total_return_pct: float
    holdings: list[HoldingOut]


class WatchIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)


class AIAnalysisOut(BaseModel):
    summary: str
    risk_score: int
    diversification: str
    suggestions: list[str]
    source: str
