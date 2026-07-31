"""Paper trading engine.

Simulated fills only. This module never contacts a broker and never moves real
money — that boundary is intentional and should stay that way.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.schemas import Fill, Lot, OrderRequest, Side
from app.services.portfolio import PortfolioStore, aggregate_positions

UTC = timezone.utc

DEFAULT_COMMISSION = 0.0
DEFAULT_SLIPPAGE_BPS = 5  # 0.05% — a realistic retail marketable-order haircut.


class InsufficientFunds(ValueError):
    pass


class InsufficientShares(ValueError):
    pass


def _fill_price(market_price: float, side: Side, slippage_bps: int) -> float:
    drift = market_price * slippage_bps / 10_000
    return round(market_price + drift if side is Side.BUY else market_price - drift, 4)


def execute(
    store: PortfolioStore,
    order: OrderRequest,
    market_price: float,
    commission: float = DEFAULT_COMMISSION,
    slippage_bps: int = DEFAULT_SLIPPAGE_BPS,
) -> Fill:
    symbol = order.symbol.upper()
    price = _fill_price(market_price, order.side, slippage_bps)

    if order.limit_price is not None:
        crosses = (
            price <= order.limit_price if order.side is Side.BUY else price >= order.limit_price
        )
        if not crosses:
            raise ValueError(
                f"limit {order.limit_price} not marketable against simulated fill {price}"
            )

    if order.side is Side.BUY:
        cost = price * order.quantity + commission
        if cost > store.cash:
            raise InsufficientFunds(
                f"need ${cost:,.2f} but only ${store.cash:,.2f} cash available"
            )
        store.add_lot(
            Lot(
                symbol=symbol,
                quantity=order.quantity,
                price=price,
                trade_date=datetime.now(UTC).date(),
            )
        )
        store.set_cash(store.cash - cost)
    else:
        held = aggregate_positions(store.lots()).get(symbol, (0.0, 0.0))[0]
        if order.quantity > held + 1e-9:
            raise InsufficientShares(
                f"hold {held} shares of {symbol}, cannot sell {order.quantity}"
            )
        store.reduce_position(symbol, order.quantity)
        store.set_cash(store.cash + price * order.quantity - commission)

    return Fill(
        order_id=str(uuid.uuid4()),
        symbol=symbol,
        side=order.side,
        quantity=order.quantity,
        price=price,
        filled_at=datetime.now(UTC),
        cash_after=store.cash,
    )
