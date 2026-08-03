"""Tick store and price-socket behaviour. No network — ticks are injected."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import streaming
from app.services.streaming import Tick, TickStore, _parse_message


@pytest.fixture(autouse=True)
def clean_store():
    original = streaming.store
    streaming.store = TickStore()
    yield streaming.store
    streaming.store = original


# --- message parsing ---


@pytest.mark.parametrize(
    "message",
    [
        {"id": "NVDA", "price": 142.5},
        {"symbol": "NVDA", "price": "142.5"},
        {"id": "NVDA", "regularMarketPrice": 142.5},
    ],
)
def test_parse_accepts_field_name_variants(message):
    tick = _parse_message(message)
    assert tick is not None
    assert tick.symbol == "NVDA"
    assert tick.price == 142.5


@pytest.mark.parametrize(
    "message",
    [{}, {"id": "NVDA"}, {"price": 10.0}, {"id": "NVDA", "price": "not-a-number"}],
)
def test_parse_rejects_unusable_messages(message):
    assert _parse_message(message) is None


def test_parse_carries_change_fields():
    tick = _parse_message({"id": "NVDA", "price": 100.0, "change": 2.5, "changePercent": 2.56})
    assert tick.change == 2.5
    assert tick.change_pct == 2.56


# --- store ---


def test_snapshot_reflects_latest_price(clean_store):
    clean_store.publish(Tick("NVDA", 100.0))
    clean_store.publish(Tick("NVDA", 101.0))
    assert clean_store.snapshot()["NVDA"]["price"] == 101.0


def test_repeated_price_is_not_republished(clean_store):
    queue = clean_store.subscribe()
    clean_store.publish(Tick("NVDA", 100.0))
    clean_store.publish(Tick("NVDA", 100.0))  # Yahoo repeats the last trade

    assert queue.qsize() == 1


def test_price_change_is_published(clean_store):
    queue = clean_store.subscribe()
    clean_store.publish(Tick("NVDA", 100.0))
    clean_store.publish(Tick("NVDA", 100.5))

    assert queue.qsize() == 2


def test_change_is_derived_from_prior_close(clean_store):
    """Change and percent must agree — Yahoo sends them inconsistently."""
    clean_store.set_prev_closes({"AMD": 100.0})
    clean_store.publish(Tick("AMD", 110.0, change=999.0, change_pct=-1.9))

    payload = clean_store.snapshot()["AMD"]
    assert payload["change"] == 10.0
    assert payload["change_pct"] == 10.0


def test_change_signs_always_match(clean_store):
    clean_store.set_prev_closes({"AMD": 100.0})
    clean_store.publish(Tick("AMD", 95.0))

    payload = clean_store.snapshot()["AMD"]
    assert payload["change"] < 0 and payload["change_pct"] < 0


def test_stream_fields_used_when_prior_close_unknown(clean_store):
    clean_store.publish(Tick("ZZZZ", 50.0, change=1.0, change_pct=2.0))
    payload = clean_store.snapshot()["ZZZZ"]
    assert payload["change"] == 1.0


def test_delayed_ticks_are_not_counted_live(clean_store):
    clean_store.publish(Tick("005930.KS", 74_300.0, delayed=True))
    assert clean_store.is_live("005930.KS") is False
    assert clean_store.snapshot()["005930.KS"]["delayed"] is True


def test_stale_tick_stops_counting_as_live(clean_store):
    old = Tick("NVDA", 100.0)
    old.at = time.monotonic() - (streaming.LIVE_TTL_S + 10)
    clean_store.publish(old)

    assert clean_store.is_live("NVDA") is False
    assert clean_store.live_symbols() == set()


def test_fresh_tick_counts_as_live(clean_store):
    clean_store.publish(Tick("NVDA", 100.0))
    assert clean_store.is_live("NVDA") is True
    assert clean_store.live_symbols() == {"NVDA"}


def test_unsubscribe_stops_delivery(clean_store):
    queue = clean_store.subscribe()
    clean_store.unsubscribe(queue)
    clean_store.publish(Tick("NVDA", 100.0))

    assert queue.qsize() == 0
    assert clean_store.subscriber_count == 0


def test_slow_subscriber_is_dropped_not_blocking(clean_store):
    """A full queue must never stall the publisher."""
    queue = clean_store.subscribe()
    for i in range(600):  # queue maxsize is 500
        clean_store.publish(Tick("NVDA", 100.0 + i))

    assert queue.full()
    assert clean_store.snapshot()["NVDA"]["price"] == 100.0 + 599


# --- socket endpoint ---


def test_socket_sends_snapshot_on_connect(clean_store):
    clean_store.publish(Tick("NVDA", 142.5))
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/prices") as socket:
        message = socket.receive_json()

    assert message["type"] == "snapshot"
    assert message["prices"]["NVDA"]["price"] == 142.5


def test_socket_unsubscribes_on_disconnect(clean_store):
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/prices") as socket:
        socket.receive_json()
        assert clean_store.subscriber_count == 1

    assert clean_store.subscriber_count == 0


def test_status_reports_live_versus_delayed(clean_store):
    clean_store.publish(Tick("NVDA", 100.0))
    clean_store.publish(Tick("005930.KS", 74_300.0, delayed=True))

    report = streaming.status()
    assert "NVDA" in report["live_symbols"]
    assert "005930.KS" not in report["live_symbols"]
    assert report["kr_symbols"] > 0
