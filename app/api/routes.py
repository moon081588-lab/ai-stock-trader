"""HTTP routes. Thin — all logic lives in app/services."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.api import deps
from app.data.providers import ProviderError
from app.models.schemas import (
    DividendSummary,
    Fill,
    Forecast,
    ForecastMethod,
    IndexQuote,
    Lot,
    MarketBoard,
    MoverRow,
    NewsSummary,
    OrderRequest,
    PortfolioSummary,
    PriceHistory,
    Quote,
    StockDetail,
    WatchlistView,
)
from app.services import dividends as dividend_service
from app.services import forecast as forecast_service
from app.services import market_board as board_service
from app.services import news as news_service
from app.services import paper_trading, streaming
from app.services import portfolio as portfolio_service
from app.services import stock_detail as detail_service
from app.services import watchlist as watchlist_service

log = logging.getLogger(__name__)

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


@market.get("/indices", response_model=list[IndexQuote])
def get_indices() -> list[IndexQuote]:
    """Index cards for the dashboard grid, each with an intraday sparkline."""
    return board_service.get_indices()


@market.get("/movers", response_model=list[MoverRow])
def get_movers(
    market_filter: str = Query("all", alias="market", pattern="^(all|KR|US)$"),
    sort_by: str = Query("turnover", pattern="^(turnover|volume|market_cap|gainers|losers)$"),
    limit: int = Query(30, ge=1, le=100),
) -> list[MoverRow]:
    return board_service.get_movers(market=market_filter, sort_by=sort_by, limit=limit)


@market.get("/board", response_model=MarketBoard)
def get_board(
    market_filter: str = Query("all", alias="market", pattern="^(all|KR|US)$"),
    sort_by: str = Query("turnover", pattern="^(turnover|volume|market_cap|gainers|losers)$"),
    limit: int = Query(30, ge=1, le=100),
) -> MarketBoard:
    """Indices + movers in one round trip, so the dashboard renders in a single fetch."""
    return board_service.get_board(market=market_filter, sort_by=sort_by, limit=limit)


@market.get("/stream/status", tags=["stream"])
def stream_status() -> dict:
    """Which symbols are genuinely ticking vs. falling back to polling."""
    return streaming.status()


# --- watchlist ---

watchlist = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _watchlist_view() -> WatchlistView:
    symbols = deps.watchlist_store().symbols()
    return watchlist_service.build_view(symbols, board_service.snapshot_many(tuple(symbols)))


@watchlist.get("", response_model=WatchlistView)
def read_watchlist() -> WatchlistView:
    return _watchlist_view()


@watchlist.post("/{symbol}", response_model=WatchlistView, status_code=201)
def add_to_watchlist(symbol: str) -> WatchlistView:
    deps.watchlist_store().add(symbol)
    return _watchlist_view()


@watchlist.delete("/{symbol}", response_model=WatchlistView)
def remove_from_watchlist(symbol: str) -> WatchlistView:
    deps.watchlist_store().remove(symbol)
    return _watchlist_view()


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


# --- stock detail ---

stocks = APIRouter(prefix="/stocks", tags=["stocks"])


@stocks.get("/{symbol}", response_model=StockDetail)
def get_stock_detail(
    symbol: str,
    method: ForecastMethod = ForecastMethod.MONTE_CARLO,
    lookback_days: int = Query(detail_service.DEFAULT_LOOKBACK_DAYS, ge=90, le=3650),
) -> StockDetail:
    """Everything the 종목 상세 chart needs, minus news (fetched separately so a
    slow headline feed never blocks the price chart)."""
    try:
        bars = deps.market_data().get_history(symbol, lookback_days)
        return detail_service.build_detail(symbol, bars, method)
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


# --- live prices ---

live = APIRouter(tags=["stream"])


@live.websocket("/ws/prices")
async def stream_prices(websocket: WebSocket) -> None:
    """Push price ticks to the browser.

    Sends the full current state on connect so a late-joining tab isn't blank,
    then streams individual updates. Heartbeats keep proxies from closing an
    idle socket outside market hours.
    """
    await websocket.accept()
    queue = streaming.store.subscribe()

    try:
        await websocket.send_json({"type": "snapshot", "prices": streaming.store.snapshot()})

        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=25.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                continue

            await websocket.send_json({"type": "tick", "price": update})
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - a dead socket must not take down the server
        log.exception("price socket failed")
        with contextlib.suppress(Exception):
            await websocket.close()
    finally:
        streaming.store.unsubscribe(queue)


for sub in (market, watchlist, forecast, stocks, portfolio, news, paper, live):
    router.include_router(sub)
