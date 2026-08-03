"""Live price streaming.

Holds one WebSocket open to Yahoo's streamer (the same feed finance.yahoo.com
uses) and keeps the newest tick per symbol in memory. Browsers subscribe to the
app's own `/ws/prices`, so however many tabs are open, there is exactly one
upstream connection.

Symbols the streamer never delivers — Korean listings, typically — fall back to
a polling loop and are flagged `delayed` so the UI can label them honestly.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.data.universe import UNIVERSE, market_for

log = logging.getLogger(__name__)

# A symbol is considered live only if it ticked recently. Past this, the UI
# stops claiming it is live even though the socket is technically connected.
LIVE_TTL_S = 90.0
POLL_INTERVAL_S = 30.0
# The stream already carries prices. REST only supplies volume, market cap and
# prior close, which barely move — refreshing every minute was pure request
# pressure, and getting throttled is what emptied the table.
BOARD_REFRESH_S = 300.0
RECONNECT_BASE_S = 2.0
RECONNECT_MAX_S = 60.0


@dataclass
class Tick:
    symbol: str
    price: float
    change: float | None = None
    change_pct: float | None = None
    at: float = field(default_factory=time.monotonic)
    delayed: bool = False

    def as_payload(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": round(self.price, 4),
            "change": round(self.change, 4) if self.change is not None else None,
            "change_pct": round(self.change_pct, 2) if self.change_pct is not None else None,
            "delayed": self.delayed,
        }


class TickStore:
    """Newest tick per symbol, plus a fan-out to connected browsers."""

    def __init__(self) -> None:
        self._ticks: dict[str, Tick] = {}
        self._subscribers: set[asyncio.Queue] = set()
        self._prev_closes: dict[str, float] = {}

    def set_prev_closes(self, closes: dict[str, float]) -> None:
        """Prior closes from the daily batch, used to derive change from a tick."""
        self._prev_closes.update(closes)

    # --- reads ---

    def snapshot(self) -> dict[str, dict]:
        return {symbol: tick.as_payload() for symbol, tick in self._ticks.items()}

    def is_live(self, symbol: str) -> bool:
        tick = self._ticks.get(symbol)
        return bool(tick and not tick.delayed and time.monotonic() - tick.at < LIVE_TTL_S)

    def live_symbols(self) -> set[str]:
        return {symbol for symbol in self._ticks if self.is_live(symbol)}

    # --- writes ---

    def publish(self, tick: Tick) -> None:
        # Derive change from the prior close rather than trusting the stream's
        # own fields. Yahoo sometimes sends one and not the other, which showed
        # up in the UI as "+7.85 (-1.90%)" — a positive change with a negative
        # percent. Computing both from one number keeps them consistent.
        prev_close = self._prev_closes.get(tick.symbol)
        if prev_close:
            tick.change = tick.price - prev_close
            tick.change_pct = (tick.price / prev_close - 1) * 100

        previous = self._ticks.get(tick.symbol)
        # Yahoo repeats the last trade on some messages; suppress no-op updates
        # so the UI doesn't flash on unchanged prices.
        if previous and previous.price == tick.price and previous.delayed == tick.delayed:
            previous.at = tick.at
            return

        self._ticks[tick.symbol] = tick
        payload = tick.as_payload()
        for queue in list(self._subscribers):
            # Drop rather than block: a stalled browser must not back up the feed.
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)

    # --- subscriptions ---

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


store = TickStore()


def _parse_message(message: dict) -> Tick | None:
    """Yahoo's streamer payload. Field names vary; be liberal about what we accept."""
    symbol = message.get("id") or message.get("symbol")
    price = message.get("price") or message.get("regularMarketPrice")
    if not symbol or price is None:
        return None

    try:
        price = float(price)
    except (TypeError, ValueError):
        return None

    change = message.get("change")
    change_pct = message.get("changePercent")
    return Tick(
        symbol=str(symbol),
        price=price,
        change=float(change) if change is not None else None,
        change_pct=float(change_pct) if change_pct is not None else None,
    )


class PriceStreamer:
    """Owns the upstream socket and the polling fallback."""

    def __init__(self, symbols: list[str] | None = None) -> None:
        self.symbols = symbols or [spec.symbol for spec in UNIVERSE]
        self._tasks: list[asyncio.Task] = []
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        self._stopping.clear()
        self._tasks = [
            asyncio.create_task(self._stream_loop(), name="yahoo-stream"),
            asyncio.create_task(self._poll_loop(), name="delayed-poll"),
            asyncio.create_task(self._board_loop(), name="board-refresh"),
        ]
        log.info("price streamer started for %d symbols", len(self.symbols))

    async def _board_loop(self) -> None:
        """Keep the board state fresh so HTTP reads never touch the network."""
        from app.services.market_board import refresh_board

        while not self._stopping.is_set():
            try:
                await asyncio.to_thread(refresh_board)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("board refresh failed: %s", exc)

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=BOARD_REFRESH_S)

    async def stop(self) -> None:
        self._stopping.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []
        log.info("price streamer stopped")

    async def _stream_loop(self) -> None:
        """Reconnect with exponential backoff. Yahoo drops idle sockets routinely."""
        backoff = RECONNECT_BASE_S

        while not self._stopping.is_set():
            socket = None
            try:
                import yfinance as yf

                # AsyncWebSocket documents no __aenter__, so manage it explicitly.
                # verbose=False keeps its own prints out of the uvicorn log.
                socket = yf.AsyncWebSocket(verbose=False)
                await socket.subscribe(self.symbols)
                log.info("yahoo stream connected (%d symbols)", len(self.symbols))
                backoff = RECONNECT_BASE_S

                # listen() types the handler as a plain sync callable.
                def on_message(message: dict) -> None:
                    tick = _parse_message(message)
                    if tick:
                        store.publish(tick)

                await socket.listen(on_message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - undocumented endpoint, expect churn
                log.warning("yahoo stream dropped (%s); retrying in %.0fs", exc, backoff)
            finally:
                if socket is not None:
                    with contextlib.suppress(Exception):
                        await socket.close()

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=backoff)
            backoff = min(backoff * 2, RECONNECT_MAX_S)

    async def _poll_loop(self) -> None:
        """Fill in whatever the stream isn't delivering, flagged as delayed."""
        from app.services.market_board import batch_snapshots

        while not self._stopping.is_set():
            try:
                stale = [s for s in self.symbols if not store.is_live(s)]
                if stale:
                    snapshots = await asyncio.to_thread(batch_snapshots, tuple(stale))
                    for symbol, snap in snapshots.items():
                        store.publish(
                            Tick(
                                symbol=symbol,
                                price=snap["price"],
                                change=snap["change"],
                                change_pct=snap["change_pct"],
                                delayed=True,
                            )
                        )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("delayed poll failed: %s", exc)

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=POLL_INTERVAL_S)


streamer = PriceStreamer()


def status() -> dict:
    """Diagnostics for the UI badge and for debugging a quiet feed."""
    from app.services.market_board import health as board_health

    live = store.live_symbols()
    return {
        "board": board_health(),
        "connected_browsers": store.subscriber_count,
        "tracked_symbols": len(streamer.symbols),
        "live_symbols": sorted(live),
        "live_count": len(live),
        "delayed_count": len(streamer.symbols) - len(live),
        "kr_symbols": sum(1 for s in streamer.symbols if market_for(s) == "KR"),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
