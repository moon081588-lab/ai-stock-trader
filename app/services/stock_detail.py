"""Composes the 종목 상세 payload: quote, history, projection, and risk metrics."""

from __future__ import annotations

from app.core import analytics
from app.data.universe import BY_SYMBOL
from app.models.schemas import Bar, ForecastMethod, RiskMetrics, StockDetail
from app.services.forecast import build_forecast

# Enough history for the chart to show context, and for the risk metrics to mean
# something. Under ~250 bars, Sharpe and max drawdown are mostly noise.
DEFAULT_LOOKBACK_DAYS = 730


def build_metrics(bars: list[Bar]) -> RiskMetrics:
    return RiskMetrics(
        cagr_pct=round(analytics.cagr(bars) * 100, 2),
        sharpe_ratio=round(analytics.sharpe_ratio(bars), 2),
        max_drawdown_pct=round(analytics.max_drawdown(bars) * 100, 2),
        annualized_volatility_pct=round(
            analytics.daily_returns(bars).std(ddof=1) * (252**0.5) * 100, 2
        ),
        value_at_risk_95_pct=round(analytics.value_at_risk(bars) * 100, 2),
    )


def build_detail(
    symbol: str,
    bars: list[Bar],
    method: ForecastMethod = ForecastMethod.MONTE_CARLO,
) -> StockDetail:
    if len(bars) < 30:
        raise ValueError(f"{symbol}: need at least 30 bars of history, got {len(bars)}")

    spec = BY_SYMBOL.get(symbol.upper())
    last, prev = bars[-1].close, bars[-2].close

    return StockDetail(
        symbol=symbol.upper(),
        name=spec.name if spec else symbol.upper(),
        market=spec.market if spec else "US",
        kind=spec.kind if spec else "stock",
        price=round(last, 2),
        change=round(last - prev, 2),
        change_pct=round((last / prev - 1) * 100, 2) if prev else 0.0,
        bars=bars,
        forecast=build_forecast(symbol, bars, method),
        metrics=build_metrics(bars),
    )
