"""Upcoming earnings dates for the tracked universe.

Deliberately narrow: this is an *earnings* calendar, not the macro calendar
Toss shows (ISM, ADP, nonfarm payrolls). Those come from an economic-data
vendor we don't have. Promising "주요 일정" and then only listing earnings
would be misleading, so the response carries a note saying what's missing.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta, timezone

from app.data.cache import ttl_cache
from app.data.universe import UNIVERSE
from app.models.schemas import CalendarView, EarningsEvent

log = logging.getLogger(__name__)

MAX_WORKERS = 6
LOOKAHEAD_DAYS = 45
# Earnings dates move rarely. A long TTL keeps this off the hot path — the
# per-ticker calendar endpoint has no batch equivalent, so it's 24 requests.
CACHE_TTL_S = 6 * 60 * 60
FETCH_BUDGET_S = 12.0


def _next_earnings(symbol: str) -> date | None:
    try:
        import yfinance as yf

        calendar = yf.Ticker(symbol).calendar or {}
        dates = calendar.get("Earnings Date") or []
        if isinstance(dates, (date, datetime)):
            dates = [dates]

        today = datetime.now(timezone.utc).date()
        upcoming = sorted(
            d.date() if isinstance(d, datetime) else d
            for d in dates
            if d is not None
        )
        return next((d for d in upcoming if d >= today), None)
    except Exception:  # noqa: BLE001 - a missing date must not fail the card
        return None


@ttl_cache(ttl=CACHE_TTL_S, prefix="earnings")
def upcoming_earnings() -> CalendarView:
    """Next earnings date per symbol, within the lookahead window."""
    symbols = [spec.symbol for spec in UNIVERSE if spec.kind == "stock"]

    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        futures = {pool.submit(_next_earnings, s): s for s in symbols}
        done, pending = wait(futures, timeout=FETCH_BUDGET_S)
        if pending:
            log.info("earnings calendar budget hit; %d lookups dropped", len(pending))

        found: dict[str, date] = {}
        for future in done:
            when = future.result()
            if when is not None:
                found[futures[future]] = when
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=LOOKAHEAD_DAYS)
    from app.data.universe import BY_SYMBOL

    events = [
        EarningsEvent(
            symbol=symbol,
            name=BY_SYMBOL[symbol].name,
            market=BY_SYMBOL[symbol].market,
            event_date=when,
            days_away=(when - today).days,
        )
        for symbol, when in found.items()
        if today <= when <= horizon
    ]

    log.info("earnings calendar: %d events within %d days", len(events), LOOKAHEAD_DAYS)
    return CalendarView(events=sorted(events, key=lambda e: e.event_date))
