"""Risk and performance metrics shared by the forecasting and portfolio layers."""

from __future__ import annotations

import math

import numpy as np

from app.models.schemas import Bar

TRADING_DAYS = 252


def daily_returns(bars: list[Bar]) -> np.ndarray:
    closes = np.array([b.close for b in bars], dtype=float)
    return np.diff(closes) / closes[:-1]


def cagr(bars: list[Bar]) -> float:
    """Compound annual growth rate over the sample."""
    if len(bars) < 2:
        return 0.0
    years = (bars[-1].date - bars[0].date).days / 365.25
    if years <= 0 or bars[0].close <= 0:
        return 0.0
    return float((bars[-1].close / bars[0].close) ** (1 / years) - 1)


def sharpe_ratio(bars: list[Bar], risk_free_rate: float = 0.04) -> float:
    """Annualized excess return per unit of volatility."""
    rets = daily_returns(bars)
    if rets.size < 2 or rets.std(ddof=1) == 0:
        return 0.0
    excess = rets.mean() * TRADING_DAYS - risk_free_rate
    return float(excess / (rets.std(ddof=1) * math.sqrt(TRADING_DAYS)))


def max_drawdown(bars: list[Bar]) -> float:
    """Largest peak-to-trough decline, as a negative fraction."""
    closes = np.array([b.close for b in bars], dtype=float)
    if closes.size == 0:
        return 0.0
    running_peak = np.maximum.accumulate(closes)
    return float((closes / running_peak - 1).min())


def beta(asset_bars: list[Bar], benchmark_bars: list[Bar]) -> float:
    """Sensitivity to the benchmark. Series are truncated to a common length."""
    a, b = daily_returns(asset_bars), daily_returns(benchmark_bars)
    n = min(a.size, b.size)
    if n < 2 or b[-n:].var(ddof=1) == 0:
        return 0.0
    return float(np.cov(a[-n:], b[-n:], ddof=1)[0][1] / b[-n:].var(ddof=1))


def value_at_risk(bars: list[Bar], confidence: float = 0.95) -> float:
    """Historical one-day VaR as a negative fraction of position value."""
    rets = daily_returns(bars)
    if rets.size == 0:
        return 0.0
    return float(np.percentile(rets, (1 - confidence) * 100))
