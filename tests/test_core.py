"""Tests for the pure-logic layer — no network calls."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from app.core import analytics
from app.data import cache
from app.data.universe import INDICES, UNIVERSE, display_name
from app.models.schemas import Bar, ForecastMethod, Lot, OrderRequest, Side
from app.services import (
    dividends,
    forecast,
    paper_trading,
    portfolio,
    stock_detail,
    watchlist,
)
from app.services.news import LexiconSentimentScorer


def make_bars(n: int = 300, start: float = 100.0, daily_drift: float = 0.0005) -> list[Bar]:
    bars, price, day = [], start, date(2024, 1, 1)
    for i in range(n):
        price *= math.exp(daily_drift + 0.001 * math.sin(i))
        bars.append(
            Bar(
                date=day + timedelta(days=i),
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1_000_000,
            )
        )
    return bars


# --- forecasting ---


@pytest.mark.parametrize("method", list(ForecastMethod))
def test_forecast_produces_ordered_bands(method):
    result = forecast.build_forecast("TEST", make_bars(), method)
    assert result.symbol == "TEST"
    assert len(result.points) == len(forecast.DEFAULT_HORIZONS)
    for point in result.points:
        assert point.low <= point.expected_price <= point.high
        assert 0 < point.confidence <= 1


def test_forecast_confidence_decays_with_horizon():
    points = forecast.build_forecast("TEST", make_bars()).points
    assert points[0].confidence > points[-1].confidence


def test_forecast_rejects_short_history():
    with pytest.raises(ValueError, match="at least 30 bars"):
        forecast.build_forecast("TEST", make_bars(10))


def test_upward_drift_projects_higher_price():
    result = forecast.build_forecast("TEST", make_bars(daily_drift=0.001), ForecastMethod.DRIFT)
    assert result.expected_return_pct > 0


# --- portfolio ---


def test_aggregate_positions_averages_cost():
    lots = [
        Lot(symbol="AAPL", quantity=10, price=100, trade_date=date(2024, 1, 1)),
        Lot(symbol="AAPL", quantity=10, price=200, trade_date=date(2024, 6, 1)),
    ]
    assert portfolio.aggregate_positions(lots)["AAPL"] == (20.0, 150.0)


def test_summarize_computes_pl_and_weights():
    lots = [
        Lot(symbol="AAPL", quantity=10, price=100, trade_date=date(2024, 1, 1)),
        Lot(symbol="MSFT", quantity=5, price=200, trade_date=date(2024, 1, 1)),
    ]
    summary = portfolio.summarize(lots, cash=1_000, prices={"AAPL": 150, "MSFT": 200})

    assert summary.market_value == 2_500
    assert summary.total_value == 3_500
    assert summary.unrealized_pl == 500
    assert sum(p.weight for p in summary.positions) == pytest.approx(100, abs=0.1)


def test_unpriced_position_does_not_fake_a_loss():
    lots = [
        Lot(symbol="AAPL", quantity=10, price=100, trade_date=date(2024, 1, 1)),
        Lot(symbol="XYZ", quantity=1, price=500, trade_date=date(2024, 1, 1)),
    ]
    summary = portfolio.summarize(lots, cash=0, prices={"AAPL": 110})

    unpriced = next(p for p in summary.positions if p.symbol == "XYZ")
    assert unpriced.market_value is None
    # P/L reflects only the priced AAPL lot, not a phantom -100% on XYZ.
    assert summary.unrealized_pl == 100
    assert summary.unrealized_pl_pct == 10.0


# --- store + paper trading ---


@pytest.fixture
def store(tmp_path):
    return portfolio.PortfolioStore(tmp_path / "p.json", starting_cash=10_000)


def test_buy_reduces_cash_and_adds_lot(store):
    order = OrderRequest(symbol="AAPL", side=Side.BUY, quantity=10)
    fill = paper_trading.execute(store, order, 100)
    assert fill.price > 100  # buy-side slippage
    assert store.cash < 10_000
    assert portfolio.aggregate_positions(store.lots())["AAPL"][0] == 10


def test_buy_beyond_cash_is_rejected(store):
    with pytest.raises(paper_trading.InsufficientFunds):
        paper_trading.execute(store, OrderRequest(symbol="AAPL", side=Side.BUY, quantity=1000), 100)


def test_sell_without_shares_is_rejected(store):
    with pytest.raises(paper_trading.InsufficientShares):
        paper_trading.execute(store, OrderRequest(symbol="AAPL", side=Side.SELL, quantity=1), 100)


def test_fifo_sell_removes_oldest_lot_first(store):
    store.add_lot(Lot(symbol="AAPL", quantity=10, price=50, trade_date=date(2024, 1, 1)))
    store.add_lot(Lot(symbol="AAPL", quantity=10, price=150, trade_date=date(2024, 6, 1)))

    basis = store.reduce_position("AAPL", 10)
    assert basis == 500  # the $50 lot, not the $150 one
    assert store.lots()[0].price == 150


def test_store_persists_across_instances(tmp_path):
    path = tmp_path / "p.json"
    first = portfolio.PortfolioStore(path, starting_cash=500)
    first.add_lot(Lot(symbol="AAPL", quantity=1, price=10, trade_date=date(2024, 1, 1)))

    assert portfolio.PortfolioStore(path).lots()[0].symbol == "AAPL"


# --- dividends ---


def test_dividends_only_credit_shares_held_by_ex_date():
    lots = [Lot(symbol="KO", quantity=100, price=60, trade_date=date(2024, 3, 1))]
    history = {
        "KO": [
            (date(2024, 2, 1), 0.48),  # before purchase — should not count
            (date(2024, 5, 1), 0.48),
            (date(2024, 8, 1), 0.48),
        ]
    }
    summary = dividends.summarize_dividends(lots, history, {"KO": 65})

    assert summary.trailing_12m_income == pytest.approx(96.0)
    assert summary.portfolio_yield_pct > 0
    assert summary.by_symbol["KO"] == pytest.approx(96.0)


def test_dividend_summary_empty_portfolio():
    summary = dividends.summarize_dividends([], {}, {})
    assert summary.trailing_12m_income == 0
    assert summary.portfolio_yield_pct == 0


# --- sentiment ---


@pytest.mark.parametrize(
    ("headline", "expected"),
    [
        ("Company beats earnings, raises guidance", 1),
        ("Shares plunge after downgrade and lawsuit", -1),
        ("Company announces annual meeting date", 0),
    ],
)
def test_lexicon_sentiment_direction(headline, expected):
    score = LexiconSentimentScorer().score(headline)
    assert (score > 0) == (expected > 0)
    assert (score < 0) == (expected < 0)


# --- risk metrics ---


def test_max_drawdown_is_negative_after_a_decline():
    bars = make_bars(60)
    bars[30].close = bars[30].close * 0.7  # inject a trough
    assert analytics.max_drawdown(bars) < -0.2


def test_max_drawdown_is_zero_for_monotonic_rise():
    assert analytics.max_drawdown(make_bars(60, daily_drift=0.002)) == pytest.approx(0, abs=1e-9)


def test_beta_against_itself_is_one():
    bars = make_bars(120)
    assert analytics.beta(bars, bars) == pytest.approx(1.0, abs=1e-6)


def test_value_at_risk_is_a_loss():
    assert analytics.value_at_risk(make_bars(200)) <= 0


def test_cagr_positive_for_rising_series():
    assert analytics.cagr(make_bars(400, daily_drift=0.001)) > 0


# --- stock detail ---


def test_detail_bundles_forecast_and_metrics():
    detail = stock_detail.build_detail("NVDA", make_bars(400))

    assert detail.symbol == "NVDA"
    assert detail.name == "엔비디아"  # resolved from the universe
    assert detail.market == "US"
    assert len(detail.bars) == 400
    assert detail.forecast.points
    assert detail.metrics.annualized_volatility_pct > 0


def test_detail_falls_back_for_unknown_symbol():
    detail = stock_detail.build_detail("ZZZZ", make_bars(200))
    assert detail.name == "ZZZZ"
    assert detail.market == "US"


def test_detail_rejects_short_history():
    with pytest.raises(ValueError, match="at least 30 bars"):
        stock_detail.build_detail("NVDA", make_bars(10))


def test_detail_change_matches_last_two_bars():
    bars = make_bars(100)
    detail = stock_detail.build_detail("NVDA", bars)
    assert detail.change == pytest.approx(bars[-1].close - bars[-2].close, abs=0.01)


# --- cache ---


def test_ttl_cache_serves_hit_then_expires(monkeypatch):
    cache.clear()
    calls = []

    @cache.ttl_cache(ttl=10, prefix="t")
    def expensive(x):
        calls.append(x)
        return x * 2

    assert expensive(3) == 6
    assert expensive(3) == 6
    assert calls == [3]  # second call served from cache

    now = [0.0]
    monkeypatch.setattr(cache.time, "monotonic", lambda: now[0])
    cache.clear()
    assert expensive(3) == 6
    now[0] = 999.0
    assert expensive(3) == 6
    assert calls == [3, 3, 3]  # expired, so recomputed


def test_cache_distinguishes_arguments():
    cache.clear()

    @cache.ttl_cache(ttl=10, prefix="args")
    def identity(x):
        return x

    assert identity(1) == 1
    assert identity(2) == 2


# --- universe / watchlist ---


def test_universe_symbols_are_unique():
    symbols = [spec.symbol for spec in UNIVERSE]
    assert len(symbols) == len(set(symbols))
    assert len({spec.key for spec in INDICES}) == len(INDICES)


def test_display_name_falls_back_to_symbol():
    assert display_name("005930.KS") == "삼성전자"
    assert display_name("UNKNOWN") == "UNKNOWN"


def test_watchlist_add_is_idempotent(tmp_path):
    store = watchlist.WatchlistStore(tmp_path / "w.json")
    store.add("NVDA")
    store.add("NVDA")
    assert store.symbols().count("NVDA") == 1

    store.remove("NVDA")
    assert "NVDA" not in store.symbols()


def test_watchlist_view_renders_unpriced_symbols():
    snapshots = {"NVDA": {"price": 100.0, "change": 1.0, "change_pct": 1.0}}
    view = watchlist.build_view(["NVDA", "005930.KS"], snapshots)

    assert [e.symbol for e in view.entries] == ["NVDA", "005930.KS"]
    assert view.entries[0].price == 100.0
    assert view.entries[1].price is None  # still listed, just without a quote

    # Market drives currency formatting in the UI — a US price shown in 원 is wrong.
    assert view.entries[0].market == "US"
    assert view.entries[1].market == "KR"


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [("NVDA", "US"), ("005930.KS", "KR"), ("123456.KQ", "KR"), ("UNKNOWN", "US")],
)
def test_market_inferred_from_symbol(symbol, expected):
    from app.data.universe import market_for

    assert market_for(symbol) == expected
