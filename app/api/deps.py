"""Shared dependency wiring for the API layer."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.data.providers import MarketDataProvider, get_provider
from app.services.news import NewsProvider, YFinanceNewsProvider
from app.services.portfolio import PortfolioStore
from app.services.watchlist import WatchlistStore


@lru_cache
def market_data() -> MarketDataProvider:
    return get_provider(get_settings().market_data_provider)


@lru_cache
def news_provider() -> NewsProvider:
    return YFinanceNewsProvider()


@lru_cache
def portfolio_store() -> PortfolioStore:
    settings = get_settings()
    return PortfolioStore(
        path=settings.data_dir / "portfolio.json",
        starting_cash=settings.paper_starting_cash,
    )


@lru_cache
def watchlist_store() -> WatchlistStore:
    return WatchlistStore(path=get_settings().data_dir / "watchlist.json")


def latest_prices(symbols: list[str]) -> dict[str, float]:
    """Best-effort quotes. A missing symbol yields no entry rather than an error."""
    provider = market_data()
    prices: dict[str, float] = {}
    for symbol in symbols:
        try:
            prices[symbol.upper()] = provider.get_quote(symbol).price
        except Exception:  # noqa: BLE001 - partial data beats a failed page
            continue
    return prices
