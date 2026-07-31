"""Builds the dashboard payload: index cards + the ranked movers table.

Fans out across the universe concurrently and caches aggressively — a single
dashboard render touches ~30 symbols, which un-cached would get rate-limited.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.data.cache import ttl_cache
from app.data.universe import INDICES, UNIVERSE, IndexSpec, TickerSpec
from app.models.schemas import IndexQuote, MarketBoard, MoverRow

log = logging.getLogger(__name__)

MAX_WORKERS = 8
SPARKLINE_POINTS = 40


def _yf():
    import yfinance as yf

    return yf


def _snapshot(symbol: str) -> dict | None:
    """Last price, prior close, and a short intraday series. None if unavailable."""
    try:
        ticker = _yf().Ticker(symbol)
        intraday = ticker.history(period="1d", interval="5m", auto_adjust=False)
        daily = ticker.history(period="5d", interval="1d", auto_adjust=False)

        if daily.empty:
            return None

        closes = [float(c) for c in daily["Close"].dropna()]
        price = float(intraday["Close"].dropna().iloc[-1]) if not intraday.empty else closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else closes[-1]

        series = (
            [float(c) for c in intraday["Close"].dropna()][-SPARKLINE_POINTS:]
            if not intraday.empty
            else closes
        )
        volume = float(daily["Volume"].dropna().iloc[-1]) if "Volume" in daily else None

        return {
            "price": price,
            "prev_close": prev_close,
            "change": price - prev_close,
            "change_pct": (price / prev_close - 1) * 100 if prev_close else 0.0,
            "series": series,
            "volume": volume,
        }
    except Exception as exc:  # noqa: BLE001 - one bad symbol must not blank the board
        log.warning("snapshot failed for %s: %s", symbol, exc)
        return None


def _market_cap(symbol: str) -> float | None:
    try:
        return float(_yf().Ticker(symbol).fast_info["market_cap"])
    except Exception:  # noqa: BLE001
        return None


def _fan_out(symbols: list[str]) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = pool.map(_snapshot, symbols)
    return {sym: snap for sym, snap in zip(symbols, results, strict=True) if snap is not None}


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


def _build_mover(rank: int, spec: TickerSpec, snap: dict, market_cap: float | None) -> MoverRow:
    price = snap["price"]
    volume = snap.get("volume")
    return MoverRow(
        rank=rank,
        symbol=spec.symbol,
        name=spec.name,
        market=spec.market,
        kind=spec.kind,
        price=round(price, 2),
        change=round(snap["change"], 2),
        change_pct=round(snap["change_pct"], 2),
        volume=volume,
        turnover=round(price * volume, 2) if volume else None,
        market_cap=market_cap,
    )


@ttl_cache(ttl=60, prefix="snapshots")
def snapshot_many(symbols: tuple[str, ...]) -> dict[str, dict]:
    """Public fan-out used by the watchlist rail. Tuple arg so it is cacheable."""
    return _fan_out(list(symbols))


@ttl_cache(ttl=60, prefix="indices")
def get_indices() -> list[IndexQuote]:
    snaps = _fan_out([spec.symbol for spec in INDICES])
    return [_build_index(spec, snaps[spec.symbol]) for spec in INDICES if spec.symbol in snaps]


@ttl_cache(ttl=60, prefix="movers")
def get_movers(
    market: str = "all",
    sort_by: str = "turnover",
    limit: int = 30,
    include_market_cap: bool = True,
) -> list[MoverRow]:
    specs = [s for s in UNIVERSE if market == "all" or s.market == market.upper()]
    snaps = _fan_out([s.symbol for s in specs])

    caps: dict[str, float | None] = {}
    if include_market_cap:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            caps = dict(
                zip(
                    [s.symbol for s in specs],
                    pool.map(_market_cap, [s.symbol for s in specs]),
                    strict=True,
                )
            )

    rows = [
        _build_mover(0, spec, snaps[spec.symbol], caps.get(spec.symbol))
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


def get_board(market: str = "all", sort_by: str = "turnover", limit: int = 30) -> MarketBoard:
    return MarketBoard(
        as_of=datetime.now(timezone.utc),
        indices=get_indices(),
        movers=get_movers(market=market, sort_by=sort_by, limit=limit),
    )
