"""Dividend income analytics across the whole portfolio."""

from __future__ import annotations

from datetime import date

from app.models.schemas import DividendSummary, Lot
from app.services.portfolio import aggregate_positions


def _shares_held_on(lots: list[Lot], symbol: str, on: date) -> float:
    """Shares of `symbol` owned on `on` — dividends only accrue to shares held by ex-date."""
    return sum(
        lot.quantity
        for lot in lots
        if lot.symbol.upper() == symbol.upper() and lot.trade_date <= on
    )


def summarize_dividends(
    lots: list[Lot],
    dividend_history: dict[str, list[tuple[date, float]]],
    prices: dict[str, float],
) -> DividendSummary:
    """Compute trailing income, forward projection, and yields.

    `dividend_history` maps symbol -> [(ex_date, amount_per_share)] for the
    trailing 12 months. Forward income assumes the trailing payout repeats,
    which understates growers and overstates cutters — treat it as a baseline.
    """
    aggregated = aggregate_positions(lots)
    by_symbol: dict[str, float] = {}
    trailing_total = 0.0
    projected_total = 0.0
    market_value = 0.0
    cost_basis = 0.0

    for symbol, (qty, avg_cost) in aggregated.items():
        price = prices.get(symbol)
        if price is not None:
            market_value += qty * price
        cost_basis += qty * avg_cost

        events = dividend_history.get(symbol, [])
        received = sum(
            amount * _shares_held_on(lots, symbol, ex_date) for ex_date, amount in events
        )
        per_share_ttm = sum(amount for _, amount in events)

        by_symbol[symbol] = round(received, 2)
        trailing_total += received
        projected_total += per_share_ttm * qty

    return DividendSummary(
        trailing_12m_income=round(trailing_total, 2),
        projected_annual_income=round(projected_total, 2),
        portfolio_yield_pct=(
            round(projected_total / market_value * 100, 2) if market_value else 0.0
        ),
        yield_on_cost_pct=round(projected_total / cost_basis * 100, 2) if cost_basis else 0.0,
        by_symbol={k: v for k, v in sorted(by_symbol.items(), key=lambda kv: -kv[1])},
        upcoming=[],  # Populated once a forward-calendar provider is wired in.
    )
