"""HTTP routes. Thin — all logic lives in app/services."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api import deps
from app.data.providers import ProviderError
from app.models.schemas import (
    DividendSummary,
    Fill,
    Forecast,
    ForecastMethod,
    Lot,
    NewsSummary,
    OrderRequest,
    PortfolioSummary,
    PriceHistory,
    Quote,
)
from app.services import dividends as dividend_service
from app.services import forecast as forecast_service
from app.services import news as news_service
from app.services import paper_trading
from app.services import portfolio as portfolio_service

router = APIRouter()


# --- market data ---

market = APIRouter(prefix="/market", tags=["market"])


@market.get("/quote/{symbol}", response_model=Quote)
def get_quote(symbol: str) -> Quote:
    try:
        return deps.market_data().get_quote(symbol)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@market.get("/history/{symbol}", response_model=PriceHistory)
def get_history(symbol: str, lookback_days: int = Query(365, ge=30, le=3650)) -> PriceHistory:
    try:
        bars = deps.market_data().get_history(symbol, lookback_days)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PriceHistory(symbol=symbol.upper(), bars=bars)


# --- forecasting ---

forecast = APIRouter(prefix="/forecast", tags=["forecast"])


@forecast.get("/{symbol}", response_model=Forecast)
def project(
    symbol: str,
    method: ForecastMethod = ForecastMethod.MONTE_CARLO,
    lookback_days: int = Query(730, ge=90, le=3650),
) -> Forecast:
    try:
        bars = deps.market_data().get_history(symbol, lookback_days)
        return forecast_service.build_forecast(symbol, bars, method)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --- portfolio ---

portfolio = APIRouter(prefix="/portfolio", tags=["portfolio"])


@portfolio.get("", response_model=PortfolioSummary)
def get_portfolio() -> PortfolioSummary:
    store = deps.portfolio_store()
    lots = store.lots()
    return portfolio_service.summarize(lots, store.cash, deps.latest_prices(store.symbols()))


@portfolio.post("/lots", response_model=PortfolioSummary, status_code=201)
def add_lot(lot: Lot) -> PortfolioSummary:
    """Record an existing holding without spending simulated cash."""
    store = deps.portfolio_store()
    store.add_lot(lot)
    lots = store.lots()
    return portfolio_service.summarize(lots, store.cash, deps.latest_prices(store.symbols()))


@portfolio.post("/reset", response_model=PortfolioSummary)
def reset_portfolio() -> PortfolioSummary:
    store = deps.portfolio_store()
    store.reset()
    return portfolio_service.summarize([], store.cash, {})


@portfolio.get("/dividends", response_model=DividendSummary)
def get_dividends(lookback_days: int = Query(365, ge=90, le=3650)) -> DividendSummary:
    store = deps.portfolio_store()
    lots = store.lots()
    provider = deps.market_data()

    history = {}
    for symbol in store.symbols():
        try:
            history[symbol] = provider.get_dividends(symbol, lookback_days)
        except ProviderError:
            history[symbol] = []

    return dividend_service.summarize_dividends(
        lots, history, deps.latest_prices(store.symbols())
    )


# --- news ---

news = APIRouter(prefix="/news", tags=["news"])


@news.get("/{symbol}", response_model=NewsSummary)
def get_news(symbol: str, limit: int = Query(20, ge=1, le=50)) -> NewsSummary:
    return news_service.summarize_news(symbol, deps.news_provider(), limit=limit)


# --- paper trading ---

paper = APIRouter(prefix="/paper", tags=["paper-trading"])


@paper.post("/orders", response_model=Fill, status_code=201)
def place_paper_order(order: OrderRequest) -> Fill:
    """Simulated fill against the last close. No real order is ever routed."""
    try:
        price = deps.market_data().get_quote(order.symbol).price
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        return paper_trading.execute(deps.portfolio_store(), order, price)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


for sub in (market, forecast, portfolio, news, paper):
    router.include_router(sub)
