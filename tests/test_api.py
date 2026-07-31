"""API contract tests against a fake provider — no network, deterministic.

These exist because the frontend's TypeScript types are hand-mirrored from the
Pydantic schemas. If a field name drifts, the UI silently renders undefined; a
contract test catches it here instead.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.data.providers import MarketDataProvider
from app.main import app
from app.models.schemas import Bar, Quote


class FakeProvider(MarketDataProvider):
    def get_history(self, symbol: str, lookback_days: int = 365) -> list[Bar]:
        bars, price, day = [], 100.0, date(2024, 1, 1)
        for i in range(min(lookback_days, 400)):
            price *= math.exp(0.0008 + 0.002 * math.sin(i / 7))
            bars.append(
                Bar(
                    date=day + timedelta(days=i),
                    open=price * 0.995,
                    high=price * 1.01,
                    low=price * 0.99,
                    close=price,
                    volume=1_000_000 + i,
                )
            )
        return bars

    def get_quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol.upper(),
            price=self.get_history(symbol, 5)[-1].close,
            as_of=datetime.now(timezone.utc),
        )

    def get_dividends(self, symbol: str, lookback_days: int = 365):
        return [(date(2024, 3, 1), 0.5), (date(2024, 9, 1), 0.5)]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "market_data", lambda: FakeProvider())
    deps.portfolio_store.cache_clear()
    deps.watchlist_store.cache_clear()

    settings = deps.get_settings()
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    yield TestClient(app)

    deps.portfolio_store.cache_clear()
    deps.watchlist_store.cache_clear()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_stock_detail_contract(client):
    body = client.get("/api/v1/stocks/NVDA").json()

    assert set(body) == {
        "symbol",
        "name",
        "market",
        "kind",
        "price",
        "change",
        "change_pct",
        "bars",
        "forecast",
        "metrics",
    }
    assert body["symbol"] == "NVDA"
    assert body["bars"][0].keys() == {"date", "open", "high", "low", "close", "volume"}
    assert set(body["metrics"]) == {
        "cagr_pct",
        "sharpe_ratio",
        "max_drawdown_pct",
        "annualized_volatility_pct",
        "value_at_risk_95_pct",
    }


def test_forecast_bands_bracket_the_median(client):
    points = client.get("/api/v1/stocks/NVDA").json()["forecast"]["points"]
    assert points
    for point in points:
        assert point["low"] <= point["expected_price"] <= point["high"]


@pytest.mark.parametrize("method", ["drift", "monte_carlo", "linear_trend"])
def test_every_forecast_method_is_accepted(client, method):
    res = client.get(f"/api/v1/stocks/NVDA?method={method}")
    assert res.status_code == 200
    assert res.json()["forecast"]["method"] == method


def test_unknown_forecast_method_is_rejected(client):
    assert client.get("/api/v1/stocks/NVDA?method=crystal_ball").status_code == 422


def test_short_lookback_is_rejected_by_validation(client):
    assert client.get("/api/v1/stocks/NVDA?lookback_days=5").status_code == 422


def test_portfolio_round_trip(client):
    client.post("/api/v1/portfolio/reset")
    res = client.post(
        "/api/v1/portfolio/lots",
        json={"symbol": "NVDA", "quantity": 10, "price": 100, "trade_date": "2024-01-15"},
    )
    assert res.status_code == 201

    body = client.get("/api/v1/portfolio").json()
    position = next(p for p in body["positions"] if p["symbol"] == "NVDA")
    assert position["quantity"] == 10
    assert position["market_value"] is not None


def test_paper_order_rejects_oversized_buy(client):
    client.post("/api/v1/portfolio/reset")
    res = client.post(
        "/api/v1/paper/orders",
        json={"symbol": "NVDA", "side": "buy", "quantity": 10_000_000},
    )
    assert res.status_code == 400
    assert "cash" in res.json()["detail"]


def test_paper_order_fills_and_debits_cash(client):
    client.post("/api/v1/portfolio/reset")
    before = client.get("/api/v1/portfolio").json()["cash"]

    fill = client.post(
        "/api/v1/paper/orders", json={"symbol": "NVDA", "side": "buy", "quantity": 1}
    ).json()

    assert fill["side"] == "buy"
    assert "Simulated" in fill["note"]
    assert client.get("/api/v1/portfolio").json()["cash"] < before


def test_watchlist_add_and_remove(client):
    added = client.post("/api/v1/watchlist/AMD").json()
    assert any(e["symbol"] == "AMD" for e in added["entries"])

    removed = client.delete("/api/v1/watchlist/AMD").json()
    assert not any(e["symbol"] == "AMD" for e in removed["entries"])


def test_market_board_never_500s_without_upstream(client):
    body = client.get("/api/v1/market/board").json()
    assert body["stale"] is True
    assert isinstance(body["indices"], list)
    assert isinstance(body["movers"], list)
