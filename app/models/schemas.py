"""Pydantic request/response models shared across the API."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Bar(BaseModel):
    """One OHLCV candle."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class Quote(BaseModel):
    symbol: str
    price: float
    currency: str = "USD"
    as_of: datetime


class PriceHistory(BaseModel):
    symbol: str
    bars: list[Bar]


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Lot(BaseModel):
    """A single purchase lot — needed for cost basis and holding-period math."""

    symbol: str
    quantity: float = Field(gt=0)
    price: float = Field(ge=0)
    trade_date: date


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    last_price: float | None = None
    market_value: float | None = None
    unrealized_pl: float | None = None
    unrealized_pl_pct: float | None = None
    weight: float | None = None


class PortfolioSummary(BaseModel):
    cash: float
    positions: list[Position]
    market_value: float
    total_value: float
    total_cost: float
    unrealized_pl: float
    unrealized_pl_pct: float


class DividendEvent(BaseModel):
    symbol: str
    ex_date: date
    amount_per_share: float
    shares_held: float
    total: float


class DividendSummary(BaseModel):
    trailing_12m_income: float
    projected_annual_income: float
    portfolio_yield_pct: float
    yield_on_cost_pct: float
    by_symbol: dict[str, float]
    upcoming: list[DividendEvent]


class ForecastMethod(str, Enum):
    DRIFT = "drift"
    MONTE_CARLO = "monte_carlo"
    LINEAR_TREND = "linear_trend"


class ForecastPoint(BaseModel):
    horizon_days: int
    expected_price: float
    low: float
    high: float
    confidence: float


class Forecast(BaseModel):
    symbol: str
    method: ForecastMethod
    last_price: float
    points: list[ForecastPoint]
    annualized_volatility: float
    expected_return_pct: float
    disclaimer: str = (
        "Statistical projection from historical data only. Not investment advice, "
        "and past performance does not predict future results."
    )


class NewsItem(BaseModel):
    symbol: str
    headline: str
    url: str | None = None
    source: str | None = None
    published_at: datetime | None = None
    sentiment: float = Field(0.0, ge=-1.0, le=1.0)


class NewsSummary(BaseModel):
    symbol: str
    item_count: int
    average_sentiment: float
    items: list[NewsItem]


class RiskMetrics(BaseModel):
    cagr_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    annualized_volatility_pct: float
    value_at_risk_95_pct: float = Field(
        description="Historical one-day VaR at 95% confidence, as a negative percent."
    )


class StockDetail(BaseModel):
    symbol: str
    name: str
    market: str
    kind: str
    price: float
    change: float
    change_pct: float
    bars: list[Bar]
    forecast: Forecast
    metrics: RiskMetrics


class IndexQuote(BaseModel):
    """One card in the market-overview grid."""

    key: str
    label: str
    symbol: str
    group: str
    price: float
    change: float
    change_pct: float
    unit: str = ""
    decimals: int = 2
    sparkline: list[float] = Field(default_factory=list)


class MoverRow(BaseModel):
    """One row of the ranked table."""

    rank: int
    symbol: str
    name: str
    market: str
    kind: str
    price: float
    change: float
    change_pct: float
    volume: float | None = None
    turnover: float | None = None
    market_cap: float | None = None


class MarketBoard(BaseModel):
    as_of: datetime
    indices: list[IndexQuote]
    movers: list[MoverRow]
    stale: bool = Field(
        True,
        description="Quotes are delayed, not live. The UI must not label them real-time.",
    )


class WatchlistEntry(BaseModel):
    symbol: str
    name: str
    market: str = "US"
    price: float | None = None
    change: float | None = None
    change_pct: float | None = None


class WatchlistView(BaseModel):
    entries: list[WatchlistEntry]


class OrderRequest(BaseModel):
    symbol: str
    side: Side
    quantity: float = Field(gt=0)
    limit_price: float | None = None


class Fill(BaseModel):
    order_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    filled_at: datetime
    cash_after: float
    note: str = "Simulated fill — no real order was placed."
