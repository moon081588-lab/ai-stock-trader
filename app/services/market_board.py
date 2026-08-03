"""Builds the dashboard payload: index cards + the ranked movers table.

Performance note: the first version fetched each symbol individually — two
history calls per ticker plus a market-cap lookup, roughly 80 upstream requests
for one page load. yfinance rate-limits hard enough that this could hang for
minutes.

Now prices come from batched `yf.download` calls (one request per timeframe, not
per symbol), sparklines are only fetched for the eight index cards that actually
draw them, and market caps run on a bounded time budget so a slow lookup can
never block the page.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone

from app.data.cache import ttl_cache
from app.data.universe import INDICES, UNIVERSE, IndexSpec, TickerSpec
from app.models.schemas import IndexQuote, MarketBoard, MoverRow, SectorPerformance

log = logging.getLogger(__name__)

MAX_WORKERS = 8
SPARKLINE_POINTS = 40
MARKET_CAP_BUDGET_S = 8.0


def _download(symbols: list[str], period: str, interval: str):
    """One batched request for all symbols. Returns None if the fetch fails."""
    import yfinance as yf

    return yf.download(
        tickers=symbols,
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )


def _frame_for(frame, symbol: str, single: bool):
    """yfinance returns flat columns for one ticker, a MultiIndex for many."""
    if frame is None or frame.empty:
        return None
    if single:
        return frame
    if symbol in frame.columns.get_level_values(0):
        sub = frame[symbol]
        return None if sub.dropna(how="all").empty else sub
    return None


def _floats(frame, column: str) -> list[float]:
    if frame is None or column not in frame:
        return []
    return [float(v) for v in frame[column].dropna()]


def batch_snapshots(symbols: tuple[str, ...], with_series: bool = False) -> dict[str, dict]:
    """Price, prior close, change, and volume for many symbols.

    `with_series` adds an intraday sparkline — a second batched request, so only
    ask for it where the UI actually draws one.
    """
    if not symbols:
        return {}

    started = time.monotonic()
    listed = list(symbols)
    single = len(listed) == 1

    try:
        daily = _download(listed, period="5d", interval="1d")
    except Exception as exc:  # noqa: BLE001 - upstream raises many types
        log.warning("daily batch failed for %d symbols: %s", len(listed), exc)
        return {}

    intraday = None
    if with_series:
        try:
            intraday = _download(listed, period="1d", interval="5m")
        except Exception as exc:  # noqa: BLE001 - sparklines are decorative
            log.warning("intraday batch failed: %s", exc)

    snapshots: dict[str, dict] = {}
    for symbol in listed:
        closes = _floats(_frame_for(daily, symbol, single), "Close")
        if not closes:
            continue

        intraday_closes = (
            _floats(_frame_for(intraday, symbol, single), "Close") if with_series else []
        )
        price = intraday_closes[-1] if intraday_closes else closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else closes[-1]
        volumes = _floats(_frame_for(daily, symbol, single), "Volume")

        snapshots[symbol] = {
            "price": price,
            "prev_close": prev_close,
            "change": price - prev_close,
            "change_pct": (price / prev_close - 1) * 100 if prev_close else 0.0,
            "series": (intraday_closes or closes)[-SPARKLINE_POINTS:],
            "volume": volumes[-1] if volumes else None,
        }

    log.info(
        "batched %d/%d symbols in %.1fs (series=%s)",
        len(snapshots),
        len(listed),
        time.monotonic() - started,
        with_series,
    )
    return snapshots


def _market_cap(symbol: str) -> float | None:
    try:
        import yfinance as yf

        return float(yf.Ticker(symbol).fast_info["market_cap"])
    except Exception:  # noqa: BLE001 - a missing cap must never fail the board
        return None


@ttl_cache(ttl=3600, prefix="marketcap")
def market_caps(symbols: tuple[str, ...]) -> dict[str, float]:
    """Best-effort market caps under a wall-clock budget.

    `fast_info` has no batch endpoint, so this is still a fan-out. Whatever
    hasn't returned when the budget expires is simply omitted — the column shows
    a dash rather than the page stalling. Cached for an hour; caps barely move.
    """
    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        futures = {pool.submit(_market_cap, symbol): symbol for symbol in symbols}
        done, pending = wait(futures, timeout=MARKET_CAP_BUDGET_S)
        if pending:
            log.info("market cap budget hit; %d lookups dropped", len(pending))

        caps: dict[str, float] = {}
        for future in done:
            value = future.result()
            if value is not None:
                caps[futures[future]] = value
        return caps
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


@ttl_cache(ttl=60, prefix="snapshots")
def snapshot_many(symbols: tuple[str, ...]) -> dict[str, dict]:
    """Public fan-out used by the watchlist rail. Tuple arg so it is cacheable."""
    return batch_snapshots(symbols)


def _build_index(spec: IndexSpec, snap: dict) -> IndexQuote:
    return IndexQuote(
        key=spec.key,
        label=spec.label,
        symbol=spec.symbol,
        group=spec.group,
        price=round(snap["price"], spec.decimals),
        change=round(snap["change"], spec.decimals),
        change_pct=round(snap["change_pct"], 2),
        unit=spec.unit,
        decimals=spec.decimals,
        sparkline=[round(v, 4) for v in snap["series"]],
    )


def _build_mover(spec: TickerSpec, snap: dict, market_cap: float | None) -> MoverRow:
    price = snap["price"]
    volume = snap.get("volume")
    return MoverRow(
        rank=0,
        symbol=spec.symbol,
        name=spec.name,
        market=spec.market,
        kind=spec.kind,
        sector=spec.sector,
        leveraged=spec.leveraged,
        price=round(price, 2),
        change=round(snap["change"], 2),
        change_pct=round(snap["change_pct"], 2),
        volume=volume,
        turnover=round(price * volume, 2) if volume else None,
        market_cap=market_cap,
    )


@ttl_cache(ttl=60, prefix="indices")
def get_indices() -> list[IndexQuote]:
    snaps = batch_snapshots(tuple(spec.symbol for spec in INDICES), with_series=True)
    return [_build_index(spec, snaps[spec.symbol]) for spec in INDICES if spec.symbol in snaps]


@ttl_cache(ttl=60, prefix="movers")
def get_movers(
    market: str = "all",
    sort_by: str = "turnover",
    limit: int = 30,
    include_market_cap: bool = True,
) -> list[MoverRow]:
    specs = [s for s in UNIVERSE if market == "all" or s.market == market.upper()]
    symbols = tuple(s.symbol for s in specs)

    # No sparklines here — the movers table doesn't draw them, so skip the
    # second batched request entirely.
    snaps = batch_snapshots(symbols)
    caps = market_caps(symbols) if include_market_cap else {}

    rows = [
        _build_mover(spec, snaps[spec.symbol], caps.get(spec.symbol))
        for spec in specs
        if spec.symbol in snaps
    ]

    keys = {
        "turnover": lambda r: r.turnover or 0,
        "volume": lambda r: r.volume or 0,
        "market_cap": lambda r: r.market_cap or 0,
        "gainers": lambda r: r.change_pct,
        "losers": lambda r: -r.change_pct,
    }
    rows.sort(key=keys.get(sort_by, keys["turnover"]), reverse=True)

    for i, row in enumerate(rows[:limit], start=1):
        row.rank = i
    return rows[:limit]


# --- background-refreshed board ---------------------------------------------
#
# HTTP requests must never wait on Yahoo. A background task refreshes this
# state on a timer; `current_board()` is a dictionary read, so the endpoint
# responds in microseconds regardless of how slow upstream is.

_state: dict = {
    "indices": [],
    "movers": [],
    "updated_at": None,
    "last_attempt": 0.0,
    "last_error": None,
}

# How long a failed refresh must wait before a request may retry it. Without
# this, an empty board made every incoming request trigger its own fetch,
# which is exactly the wrong response to being rate-limited.
RETRY_COOLDOWN_S = 30.0

# One refresh at a time. The background loop and an inline cold-start request
# could otherwise fan out simultaneously, doubling upstream load for no gain.
_refresh_lock = threading.Lock()

# How long a cold-start request will wait for an in-flight refresh. Returning an
# empty board immediately is worse than waiting: the client then sits on that
# empty response until its next poll.
REFRESH_WAIT_S = 20.0


def refresh_board(wait: bool = False) -> None:
    """Refetch and merge into module state. Runs off-request.

    Good data is never replaced with nothing. A single throttled response used
    to blank the whole table; now a failed fetch leaves the last known board in
    place and simply records the error.
    """
    acquired = (
        _refresh_lock.acquire(timeout=REFRESH_WAIT_S)
        if wait
        else _refresh_lock.acquire(blocking=False)
    )
    if not acquired:
        log.debug("refresh already in progress; skipping")
        return

    try:
        # If we waited and the other refresh already filled the board, we're done.
        if wait and is_warm():
            return
        _refresh_locked()
    finally:
        _refresh_lock.release()


def _refresh_locked() -> None:
    started = time.monotonic()
    _state["last_attempt"] = started

    indices = get_indices()
    movers = get_movers()

    if indices:
        _state["indices"] = indices
    if movers:
        _state["movers"] = movers
        # Feed prior closes to the streamer so it can derive change from a tick.
        prev_closes = {
            row.symbol: row.price - row.change for row in movers if row.change is not None
        }
        if prev_closes:
            from app.services.streaming import store as tick_store

            tick_store.set_prev_closes(prev_closes)

    if indices or movers:
        _state["updated_at"] = datetime.now(timezone.utc)

    missing = [
        name for name, fetched in (("indices", indices), ("movers", movers)) if not fetched
    ]
    _state["last_error"] = f"empty: {', '.join(missing)}" if missing else None

    log.info(
        "board refresh: %d indices, %d movers in %.1fs%s",
        len(indices),
        len(movers),
        time.monotonic() - started,
        f" (kept previous for {', '.join(missing)})" if missing else "",
    )


def current_board() -> MarketBoard:
    """Instant read of the last good refresh."""
    return MarketBoard(
        as_of=_state["updated_at"] or datetime.now(timezone.utc),
        indices=_state["indices"],
        movers=_state["movers"],
    )


def is_warm() -> bool:
    return bool(_state["movers"])


def health() -> dict:
    return {
        "warm": is_warm(),
        "indices": len(_state["indices"]),
        "movers": len(_state["movers"]),
        "updated_at": _state["updated_at"].isoformat() if _state["updated_at"] else None,
        "last_error": _state["last_error"],
    }


def get_sectors(market: str = "all") -> list[SectorPerformance]:
    """지금 뜨는 산업, computed from the board already in memory.

    This is the average move across *our tracked universe*, not the whole
    market — with roughly two dozen names a sector can be one or two stocks.
    The count is returned so the UI can say so.
    """
    rows = [
        row
        for row in _state["movers"]
        if (market == "all" or row.market == market.upper()) and not row.leveraged
    ]

    grouped: dict[str, list[MoverRow]] = {}
    for row in rows:
        grouped.setdefault(row.sector, []).append(row)

    sectors = []
    for sector, members in grouped.items():
        leader = max(members, key=lambda r: r.change_pct)
        turnovers = [r.turnover for r in members if r.turnover]
        sectors.append(
            SectorPerformance(
                sector=sector,
                change_pct=round(sum(r.change_pct for r in members) / len(members), 2),
                count=len(members),
                turnover=round(sum(turnovers), 2) if turnovers else None,
                leader_symbol=leader.symbol,
                leader_name=leader.name,
                leader_change_pct=leader.change_pct,
            )
        )

    return sorted(sectors, key=lambda s: s.change_pct, reverse=True)


def get_board(market: str = "all", sort_by: str = "turnover", limit: int = 30) -> MarketBoard:
    """Serve from memory. Only a cold, non-throttled start fetches inline."""
    if not is_warm():
        # Block on a refresh that's already running rather than returning empty.
        # Only start a fresh one if we haven't failed recently.
        cooled_down = time.monotonic() - _state["last_attempt"] > RETRY_COOLDOWN_S
        if cooled_down or _refresh_lock.locked():
            refresh_board(wait=True)

    board = current_board()
    movers = board.movers
    if market != "all":
        movers = [row for row in movers if row.market == market.upper()]

    return MarketBoard(
        as_of=board.as_of,
        indices=board.indices,
        movers=movers[:limit],
    )
