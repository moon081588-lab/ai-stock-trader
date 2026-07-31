"""Market data providers.

Everything the app needs from the outside world sits behind `MarketDataProvider`,
so swapping yfinance for Polygon/Alpha Vantage later is a one-class change.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone

from app.models.schemas import Bar, Quote

UTC = timezone.utc

log = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Raised when upstream market data is unavailable or malformed."""


class MarketDataProvider(ABC):
    @abstractmethod
    def get_history(self, symbol: str, lookback_days: int = 365) -> list[Bar]: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def get_dividends(self, symbol: str, lookback_days: int = 365) -> list[tuple[date, float]]:
        """Return (ex_date, amount_per_share) pairs."""


class YFinanceProvider(MarketDataProvider):
    """Free, no-key provider. Fine for research; rate-limited and unofficial."""

    def _ticker(self, symbol: str):
        import yfinance as yf

        return yf.Ticker(symbol.upper())

    def get_history(self, symbol: str, lookback_days: int = 365) -> list[Bar]:
        period_start = datetime.now(UTC).date() - timedelta(days=lookback_days)
        try:
            frame = self._ticker(symbol).history(start=period_start, auto_adjust=True)
        except Exception as exc:  # noqa: BLE001 - upstream raises many types
            raise ProviderError(f"history fetch failed for {symbol}: {exc}") from exc

        if frame.empty:
            raise ProviderError(f"no price history returned for {symbol}")

        return [
            Bar(
                date=idx.date(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
            for idx, row in frame.iterrows()
        ]

    def get_quote(self, symbol: str) -> Quote:
        bars = self.get_history(symbol, lookback_days=7)
        latest = bars[-1]
        return Quote(
            symbol=symbol.upper(),
            price=latest.close,
            as_of=datetime.combine(latest.date, datetime.min.time(), tzinfo=UTC),
        )

    def get_dividends(self, symbol: str, lookback_days: int = 365) -> list[tuple[date, float]]:
        cutoff = datetime.now(UTC).date() - timedelta(days=lookback_days)
        try:
            series = self._ticker(symbol).dividends
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"dividend fetch failed for {symbol}: {exc}") from exc

        return [
            (idx.date(), float(amount))
            for idx, amount in series.items()
            if idx.date() >= cutoff
        ]


def get_provider(name: str = "yfinance") -> MarketDataProvider:
    providers: dict[str, type[MarketDataProvider]] = {"yfinance": YFinanceProvider}
    if name not in providers:
        raise ValueError(f"unknown market data provider: {name}")
    return providers[name]()
