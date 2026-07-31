"""Smoke test against live data. Run: python scripts/demo.py AAPL MSFT"""

from __future__ import annotations

import sys

from app.data.providers import ProviderError, get_provider
from app.models.schemas import ForecastMethod
from app.services.forecast import build_forecast


def main(symbols: list[str]) -> int:
    provider = get_provider("yfinance")

    for symbol in symbols:
        try:
            bars = provider.get_history(symbol, lookback_days=730)
            result = build_forecast(symbol, bars, ForecastMethod.MONTE_CARLO)
        except (ProviderError, ValueError) as exc:
            print(f"{symbol}: {exc}")
            continue

        print(f"\n{result.symbol}  last ${result.last_price}")
        print(f"  annualized vol: {result.annualized_volatility:.1%}")
        for point in result.points:
            print(
                f"  {point.horizon_days:>4}d  ${point.expected_price:>9,.2f}"
                f"   [{point.low:,.2f} – {point.high:,.2f}]"
                f"   conf {point.confidence:.2f}"
            )

    print("\nProjections only. Not investment advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["AAPL"]))
