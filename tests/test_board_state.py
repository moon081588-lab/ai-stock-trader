"""The board is served from memory, so reads must never hit the network."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.models.schemas import IndexQuote, MoverRow
from app.services import market_board


def warm_indices() -> list[IndexQuote]:
    return [
        IndexQuote(
            key="kospi",
            label="코스피",
            symbol="^KS11",
            group="domestic",
            price=2700.0,
            change=10.0,
            change_pct=0.37,
        )
    ]


def make_mover(symbol: str, market: str, price: float, change: float) -> MoverRow:
    return MoverRow(
        rank=0,
        symbol=symbol,
        name=symbol,
        market=market,
        kind="stock",
        price=price,
        change=change,
        change_pct=change / (price - change) * 100,
        volume=1000,
        turnover=price * 1000,
        market_cap=None,
    )


@pytest.fixture
def warm_state():
    original = dict(market_board._state)
    market_board._state.update(
        indices=warm_indices(),
        movers=[
            make_mover("005930.KS", "KR", 74_300, 500),
            make_mover("NVDA", "US", 142.5, -2.0),
            make_mover("AMD", "US", 110.0, 10.0),
        ],
        updated_at=datetime.now(timezone.utc),
    )
    yield
    market_board._state.clear()
    market_board._state.update(original)


def test_warm_board_does_not_fetch(warm_state, monkeypatch):
    def explode() -> None:
        raise AssertionError("refresh_board must not run on a warm read")

    monkeypatch.setattr(market_board, "refresh_board", explode)
    board = market_board.get_board()

    assert len(board.movers) == 3
    assert board.stale is True  # quotes are still not exchange-grade


def test_market_filter_applies_to_cached_rows(warm_state):
    assert [r.symbol for r in market_board.get_board(market="KR").movers] == ["005930.KS"]
    assert len(market_board.get_board(market="US").movers) == 2


def test_limit_applies_to_cached_rows(warm_state):
    assert len(market_board.get_board(limit=2).movers) == 2


def test_cold_board_triggers_one_refresh(monkeypatch):
    market_board._state.update(indices=[], movers=[], updated_at=None, last_attempt=0.0)
    calls = []

    monkeypatch.setattr(market_board, "refresh_board", lambda **kw: calls.append(kw))
    market_board.get_board()

    # Waits for any in-flight refresh rather than returning an empty board.
    assert calls == [{"wait": True}]
    assert market_board.is_warm() is False  # the stub didn't populate state


def test_failed_refresh_is_not_retried_on_every_request(monkeypatch):
    """Being rate-limited must not make us fetch harder."""
    market_board._state.update(
        indices=[], movers=[], updated_at=None, last_attempt=time.monotonic()
    )
    calls = []

    monkeypatch.setattr(market_board, "refresh_board", lambda **kw: calls.append(kw))
    for _ in range(5):
        market_board.get_board()

    assert calls == []


def test_cold_request_waits_for_an_in_flight_refresh(monkeypatch):
    """The regression: a request during startup returned empty and the client
    then sat on that empty response until its next poll."""
    market_board._state.update(
        indices=[], movers=[], updated_at=None, last_attempt=time.monotonic()
    )
    calls = []
    monkeypatch.setattr(market_board, "refresh_board", lambda **kw: calls.append(kw))

    market_board._refresh_lock.acquire()
    try:
        market_board.get_board()
    finally:
        market_board._refresh_lock.release()

    # Cooldown has not elapsed, but a refresh is running — so we wait for it.
    assert calls == [{"wait": True}]


def test_concurrent_refresh_is_skipped_not_duplicated(warm_state, monkeypatch):
    ran = []
    monkeypatch.setattr(market_board, "_refresh_locked", lambda: ran.append(1))

    market_board._refresh_lock.acquire()
    try:
        market_board.refresh_board()  # non-blocking caller, e.g. the timer loop
    finally:
        market_board._refresh_lock.release()

    assert ran == []


def test_empty_fetch_keeps_the_previous_board(warm_state, monkeypatch):
    """The regression: one throttled response blanked the whole table."""
    monkeypatch.setattr(market_board, "get_indices", list)
    monkeypatch.setattr(market_board, "get_movers", list)

    market_board.refresh_board()

    assert len(market_board.current_board().movers) == 3
    assert len(market_board.current_board().indices) == 1
    assert "movers" in market_board._state["last_error"]


def test_partial_fetch_updates_only_what_succeeded(warm_state, monkeypatch):
    fresh = [make_mover("TSLA", "US", 250.0, 5.0)]
    monkeypatch.setattr(market_board, "get_indices", list)
    monkeypatch.setattr(market_board, "get_movers", lambda: fresh)

    market_board.refresh_board()

    assert [r.symbol for r in market_board.current_board().movers] == ["TSLA"]
    assert len(market_board.current_board().indices) == 1  # kept
    assert "indices" in market_board._state["last_error"]


def test_successful_refresh_clears_the_error(warm_state, monkeypatch):
    market_board._state["last_error"] = "empty: movers"
    monkeypatch.setattr(market_board, "get_indices", lambda: warm_indices())
    monkeypatch.setattr(market_board, "get_movers", lambda: [make_mover("AMD", "US", 110.0, 10.0)])

    market_board.refresh_board()
    assert market_board._state["last_error"] is None


def test_refresh_feeds_prior_closes_to_the_streamer(monkeypatch):
    from app.services import streaming

    movers = [make_mover("AMD", "US", 110.0, 10.0)]
    monkeypatch.setattr(market_board, "get_indices", list)
    monkeypatch.setattr(market_board, "get_movers", lambda: movers)

    market_board.refresh_board()

    # 110 - 10 = 100, so a later tick can derive a consistent change.
    assert streaming.store._prev_closes["AMD"] == pytest.approx(100.0)
    assert market_board.is_warm() is True
