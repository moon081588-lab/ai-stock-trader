"""Price projection.

Three deliberately simple baselines ship first. They are honest about uncertainty
and give later ML models something to beat — a forecaster that cannot outperform
drift is not worth deploying.
"""

from __future__ import annotations

import math

import numpy as np

from app.models.schemas import Bar, Forecast, ForecastMethod, ForecastPoint

TRADING_DAYS = 252
DEFAULT_HORIZONS = (5, 21, 63, 126, 252)


def _log_returns(bars: list[Bar]) -> np.ndarray:
    closes = np.array([b.close for b in bars], dtype=float)
    if len(closes) < 2:
        raise ValueError("need at least two bars to compute returns")
    return np.diff(np.log(closes))


def annualized_volatility(bars: list[Bar]) -> float:
    return float(_log_returns(bars).std(ddof=1) * math.sqrt(TRADING_DAYS))


def _drift_forecast(bars: list[Bar], horizons) -> list[ForecastPoint]:
    rets = _log_returns(bars)
    mu, sigma = float(rets.mean()), float(rets.std(ddof=1))
    last = bars[-1].close

    points = []
    for h in horizons:
        expected = last * math.exp(mu * h)
        band = sigma * math.sqrt(h)
        points.append(
            ForecastPoint(
                horizon_days=h,
                expected_price=round(expected, 2),
                low=round(last * math.exp(mu * h - 1.96 * band), 2),
                high=round(last * math.exp(mu * h + 1.96 * band), 2),
                # Confidence decays with horizon — long projections are guesses.
                confidence=round(max(0.05, 0.9 * math.exp(-h / 180)), 3),
            )
        )
    return points


def _monte_carlo_forecast(
    bars: list[Bar], horizons, simulations: int = 5_000, seed: int = 42
) -> list[ForecastPoint]:
    rets = _log_returns(bars)
    mu, sigma = float(rets.mean()), float(rets.std(ddof=1))
    last = bars[-1].close
    rng = np.random.default_rng(seed)

    points = []
    for h in horizons:
        shocks = rng.normal(mu, sigma, size=(simulations, h)).sum(axis=1)
        prices = last * np.exp(shocks)
        points.append(
            ForecastPoint(
                horizon_days=h,
                expected_price=round(float(np.median(prices)), 2),
                low=round(float(np.percentile(prices, 5)), 2),
                high=round(float(np.percentile(prices, 95)), 2),
                confidence=round(max(0.05, 0.9 * math.exp(-h / 180)), 3),
            )
        )
    return points


def _linear_trend_forecast(bars: list[Bar], horizons) -> list[ForecastPoint]:
    closes = np.array([b.close for b in bars], dtype=float)
    x = np.arange(len(closes), dtype=float)
    slope, intercept = np.polyfit(x, closes, 1)
    residual_std = float((closes - (slope * x + intercept)).std(ddof=1))

    points = []
    for h in horizons:
        expected = float(slope * (len(closes) - 1 + h) + intercept)
        band = 1.96 * residual_std * math.sqrt(1 + h / len(closes))
        points.append(
            ForecastPoint(
                horizon_days=h,
                expected_price=round(max(expected, 0.0), 2),
                low=round(max(expected - band, 0.0), 2),
                high=round(expected + band, 2),
                confidence=round(max(0.05, 0.75 * math.exp(-h / 180)), 3),
            )
        )
    return points


_METHODS = {
    ForecastMethod.DRIFT: _drift_forecast,
    ForecastMethod.MONTE_CARLO: _monte_carlo_forecast,
    ForecastMethod.LINEAR_TREND: _linear_trend_forecast,
}


def build_forecast(
    symbol: str,
    bars: list[Bar],
    method: ForecastMethod = ForecastMethod.MONTE_CARLO,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> Forecast:
    if len(bars) < 30:
        raise ValueError(f"{symbol}: need at least 30 bars of history, got {len(bars)}")

    points = _METHODS[method](bars, horizons)
    last = bars[-1].close
    one_year = next((p for p in points if p.horizon_days == 252), points[-1])

    return Forecast(
        symbol=symbol.upper(),
        method=method,
        last_price=round(last, 2),
        points=points,
        annualized_volatility=round(annualized_volatility(bars), 4),
        expected_return_pct=round((one_year.expected_price / last - 1) * 100, 2),
    )
