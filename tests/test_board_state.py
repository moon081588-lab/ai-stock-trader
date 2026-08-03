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


def make_mover(
    symbol: str,
    market: str,
    price: float,
    change: float,
    sector: str = "반도체",
    leveraged: bool = False,
) -> MoverRow:
    return MoverRow(
        rank=0,
        symbol=symbol,
        name=symbol,
        market=market,
        kind="stock",
        sector=sector,
        leveraged=leveraged,
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


def test_sectors_average_members_and_name_the_leader():
    market_board._state.update(
        movers=[
            make_mover("A", "KR", 100, 10, sector="반도체"),  # +11.11%
            make_mover("B", "KR", 100, 2, sector="반도체"),  # +2.04%
            make_mover("C", "US", 100, -5, sector="자동차"),
        ],
        updated_at=datetime.now(timezone.utc),
    )

    sectors = {s.sector: s for s in market_board.get_sectors()}

    assert sectors["반도체"].count == 2
    assert sectors["반도체"].leader_symbol == "A"
    assert sectors["자동차"].change_pct < 0
    # Sorted best-first.
    assert market_board.get_sectors()[0].sector == "반도체"


def test_sectors_exclude_leveraged_products():
    """A 3x ETF moving 15% would swamp the average of the sector it sits in."""
    market_board._state.update(
        movers=[
            make_mover("REAL", "US", 100, 1, sector="반도체"),
            make_mover("LEV", "US", 100, 30, sector="반도체", leveraged=True),
        ],
        updated_at=datetime.now(timezone.utc),
    )

    sectors = market_board.get_sectors()
    assert len(sectors) == 1
    assert sectors[0].count == 1
    assert sectors[0].leader_symbol == "REAL"


def test_sectors_respect_the_market_filter():
    market_board._state.update(
        movers=[
            make_mover("KR1", "KR", 100, 5, sector="반도체"),
            make_mover("US1", "US", 100, 5, sector="자동차"),
        ],
        updated_at=datetime.now(timezone.utc),
    )

    assert [s.sector for s in market_board.get_sectors(market="KR")] == ["반도체"]
    assert [s.sector for s in market_board.get_sectors(market="US")] == ["자동차"]


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
