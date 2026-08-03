"""Static universe config: which indices and tickers the dashboard tracks.

Names live here rather than being fetched. yfinance's metadata endpoints are slow
and occasionally return nothing; a hardcoded label never fails to render.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexSpec:
    key: str
    label: str
    symbol: str
    group: str  # "domestic" | "global" | "macro"
    decimals: int = 2
    unit: str = ""


INDICES: tuple[IndexSpec, ...] = (
    IndexSpec("kospi", "코스피", "^KS11", "domestic"),
    IndexSpec("kosdaq", "코스닥", "^KQ11", "domestic"),
    IndexSpec("usdkrw", "달러 환율", "KRW=X", "macro", unit="원"),
    IndexSpec("vix", "VIX", "^VIX", "macro"),
    IndexSpec("nasdaq", "나스닥", "^IXIC", "global"),
    IndexSpec("sp500", "S&P 500", "^GSPC", "global"),
    IndexSpec("sox", "필라델피아 반도체", "^SOX", "global"),
    IndexSpec("btc", "비트코인", "BTC-KRW", "macro", decimals=0, unit="원"),
)


@dataclass(frozen=True)
class TickerSpec:
    symbol: str
    name: str
    market: str  # "KR" | "US"
    kind: str = "stock"  # "stock" | "etf"


UNIVERSE: tuple[TickerSpec, ...] = (
    # --- Korea ---
    TickerSpec("005930.KS", "삼성전자", "KR"),
    TickerSpec("000660.KS", "SK하이닉스", "KR"),
    TickerSpec("009150.KS", "삼성전기", "KR"),
    TickerSpec("005380.KS", "현대차", "KR"),
    TickerSpec("042700.KS", "한미반도체", "KR"),
    TickerSpec("298040.KS", "효성중공업", "KR"),
    TickerSpec("373220.KS", "LG에너지솔루션", "KR"),
    TickerSpec("035420.KS", "NAVER", "KR"),
    TickerSpec("035720.KS", "카카오", "KR"),
    TickerSpec("068270.KS", "셀트리온", "KR"),
    TickerSpec("122630.KS", "KODEX 레버리지", "KR", "etf"),
    TickerSpec("069500.KS", "KODEX 200", "KR", "etf"),
    # --- US ---
    TickerSpec("NVDA", "엔비디아", "US"),
    TickerSpec("AAPL", "애플", "US"),
    TickerSpec("MSFT", "마이크로소프트", "US"),
    TickerSpec("TSLA", "테슬라", "US"),
    TickerSpec("AMD", "AMD", "US"),
    TickerSpec("AVGO", "브로드컴", "US"),
    TickerSpec("GOOGL", "알파벳", "US"),
    TickerSpec("AMZN", "아마존", "US"),
    TickerSpec("META", "메타", "US"),
    TickerSpec("SOXL", "SOXL", "US", "etf"),
    TickerSpec("TQQQ", "TQQQ", "US", "etf"),
    TickerSpec("SPY", "SPY", "US", "etf"),
)

BY_SYMBOL: dict[str, TickerSpec] = {spec.symbol: spec for spec in UNIVERSE}


def display_name(symbol: str) -> str:
    spec = BY_SYMBOL.get(symbol.upper()) or BY_SYMBOL.get(symbol)
    return spec.name if spec else symbol.upper()


def market_for(symbol: str) -> str:
    """Which market a symbol trades in — decides currency formatting in the UI."""
    spec = BY_SYMBOL.get(symbol.upper()) or BY_SYMBOL.get(symbol)
    if spec:
        return spec.market
    # Yahoo suffixes Korean listings; anything else is treated as US.
    return "KR" if symbol.upper().endswith((".KS", ".KQ")) else "US"
