"""Portfolio state: lots, positions, cash, and valuation.

Persisted as JSON so the app survives restarts without a database. Swap
`JsonPortfolioStore` for a SQL-backed store when multi-user support arrives.
"""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone
from pathlib import Path

from app.models.schemas import Lot, PortfolioSummary, Position


class PortfolioStore:
    """Thread-safe JSON-backed store of lots and cash."""

    def __init__(self, path: Path, starting_cash: float = 100_000.0):
        self.path = path
        self._lock = threading.Lock()
        self._starting_cash = starting_cash
        self._state = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"cash": self._starting_cash, "lots": []}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._state, indent=2, default=str))

    # --- reads ---

    @property
    def cash(self) -> float:
        return float(self._state["cash"])

    def lots(self) -> list[Lot]:
        return [Lot(**lot) for lot in self._state["lots"]]

    def symbols(self) -> list[str]:
        return sorted({lot.symbol for lot in self.lots()})

    # --- writes ---

    def add_lot(self, lot: Lot) -> None:
        with self._lock:
            self._state["lots"].append(json.loads(lot.model_dump_json()))
            self._save()

    def set_cash(self, amount: float) -> None:
        with self._lock:
            self._state["cash"] = round(amount, 2)
            self._save()

    def reduce_position(self, symbol: str, quantity: float) -> float:
        """Sell FIFO. Returns realized cost basis of the shares removed."""
        with self._lock:
            remaining = quantity
            basis = 0.0
            kept: list[dict] = []

            for raw in self._state["lots"]:
                lot = Lot(**raw)
                if lot.symbol != symbol.upper() or remaining <= 0:
                    kept.append(raw)
                    continue

                take = min(lot.quantity, remaining)
                basis += take * lot.price
                remaining -= take
                if lot.quantity > take:
                    raw = {**raw, "quantity": lot.quantity - take}
                    kept.append(raw)

            if remaining > 1e-9:
                raise ValueError(f"not enough shares of {symbol} to sell {quantity}")

            self._state["lots"] = kept
            self._save()
            return round(basis, 2)

    def reset(self) -> None:
        with self._lock:
            self._state = {"cash": self._starting_cash, "lots": []}
            self._save()


def aggregate_positions(lots: list[Lot]) -> dict[str, tuple[float, float]]:
    """Collapse lots into {symbol: (total_quantity, average_cost)}."""
    totals: dict[str, list[float]] = {}
    for lot in lots:
        qty, cost = totals.setdefault(lot.symbol.upper(), [0.0, 0.0])
        totals[lot.symbol.upper()] = [qty + lot.quantity, cost + lot.quantity * lot.price]

    return {
        symbol: (round(qty, 6), round(cost / qty, 4) if qty else 0.0)
        for symbol, (qty, cost) in totals.items()
    }


def summarize(
    lots: list[Lot], cash: float, prices: dict[str, float]
) -> PortfolioSummary:
    aggregated = aggregate_positions(lots)
    positions: list[Position] = []
    market_value = 0.0
    total_cost = 0.0
    # Unpriced positions are excluded from P/L — comparing a known cost against a
    # missing market value would report a fake 100% loss.
    priced_cost = 0.0

    for symbol, (qty, avg_cost) in aggregated.items():
        price = prices.get(symbol)
        value = qty * price if price is not None else None
        cost = qty * avg_cost
        total_cost += cost
        if value is not None:
            market_value += value
            priced_cost += cost

        positions.append(
            Position(
                symbol=symbol,
                quantity=qty,
                avg_cost=round(avg_cost, 4),
                last_price=round(price, 2) if price is not None else None,
                market_value=round(value, 2) if value is not None else None,
                unrealized_pl=round(value - cost, 2) if value is not None else None,
                unrealized_pl_pct=(
                    round((value / cost - 1) * 100, 2) if value is not None and cost else None
                ),
            )
        )

    for position in positions:
        if position.market_value is not None and market_value:
            position.weight = round(position.market_value / market_value * 100, 2)

    unrealized = market_value - priced_cost
    return PortfolioSummary(
        cash=round(cash, 2),
        positions=sorted(positions, key=lambda p: p.market_value or 0, reverse=True),
        market_value=round(market_value, 2),
        total_value=round(market_value + cash, 2),
        total_cost=round(total_cost, 2),
        unrealized_pl=round(unrealized, 2),
        unrealized_pl_pct=round(unrealized / priced_cost * 100, 2) if priced_cost else 0.0,
    )


def today() -> date:
    return datetime.now(timezone.utc).date()
