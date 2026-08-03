"""Static universe config: which indices and tickers the dashboard tracks.

Names, sectors and risk flags live here rather than being fetched. yfinance's
metadata endpoints are slow and occasionally return nothing; a hardcoded label
never fails to render, and sector strings from Yahoo are inconsistent between
Korean and US listings anyway.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexSpec:
    key: str
    label: str
    symbol: str
    # "domestic" | "macro" | "global" render as cards.
    # "ticker" appears only in the bottom bar.
    group: str
    decimals: int = 2
    unit: str = ""


CARD_GROUPS = ("domestic", "macro", "global")

# Korean and US headline indices only, plus the macro readings that sit
# alongside them on every Korean brokerage dashboard.
INDICES: tuple[IndexSpec, ...] = (
    IndexSpec("kospi", "코스피", "^KS11", "domestic"),
    IndexSpec("kosdaq", "코스닥", "^KQ11", "domestic"),
    IndexSpec("usdkrw", "달러 환율", "KRW=X", "macro", unit="원"),
    IndexSpec("vix", "VIX", "^VIX", "macro"),
    IndexSpec("nasdaq", "나스닥", "^IXIC", "global"),
    IndexSpec("sp500", "S&P 500", "^GSPC", "global"),
    IndexSpec("dxy", "달러 인덱스", "DX-Y.NYB", "ticker"),
)

USDKRW_KEY = "usdkrw"


@dataclass(frozen=True)
class TickerSpec:
    symbol: str
    name: str
    market: str  # "KR" | "US"
    sector: str
    kind: str = "stock"  # "stock" | "etf"
    # Leveraged and inverse products. Hidden by 투자위험 종목 숨기기, because a
    # 3x ETF moving 15% in a day is not comparable to a stock doing the same.
    leveraged: bool = False


UNIVERSE: tuple[TickerSpec, ...] = (
    # --- Korea ---
    TickerSpec("005930.KS", "삼성전자", "KR", "반도체"),
    TickerSpec("000660.KS", "SK하이닉스", "KR", "반도체"),
    TickerSpec("009150.KS", "삼성전기", "KR", "전자부품"),
    TickerSpec("005380.KS", "현대차", "KR", "자동차"),
    TickerSpec("042700.KS", "한미반도체", "KR", "반도체"),
    TickerSpec("298040.KS", "효성중공업", "KR", "중공업"),
    TickerSpec("373220.KS", "LG에너지솔루션", "KR", "2차전지"),
    TickerSpec("035420.KS", "NAVER", "KR", "인터넷"),
    TickerSpec("035720.KS", "카카오", "KR", "인터넷"),
    TickerSpec("068270.KS", "셀트리온", "KR", "바이오"),
    TickerSpec("122630.KS", "KODEX 레버리지", "KR", "ETF", "etf", leveraged=True),
    TickerSpec("069500.KS", "KODEX 200", "KR", "ETF", "etf"),
    # --- US ---
    TickerSpec("NVDA", "엔비디아", "US", "반도체"),
    TickerSpec("AAPL", "애플", "US", "하드웨어"),
    TickerSpec("MSFT", "마이크로소프트", "US", "소프트웨어"),
    TickerSpec("TSLA", "테슬라", "US", "자동차"),
    TickerSpec("AMD", "AMD", "US", "반도체"),
    TickerSpec("AVGO", "브로드컴", "US", "반도체"),
    TickerSpec("GOOGL", "알파벳", "US", "인터넷"),
    TickerSpec("AMZN", "아마존", "US", "이커머스"),
    TickerSpec("META", "메타", "US", "인터넷"),
    TickerSpec("SOXL", "SOXL", "US", "ETF", "etf", leveraged=True),
    TickerSpec("TQQQ", "TQQQ", "US", "ETF", "etf", leveraged=True),
    TickerSpec("SPY", "SPY", "US", "ETF", "etf"),
)

BY_SYMBOL: dict[str, TickerSpec] = {spec.symbol: spec for spec in UNIVERSE}


def _spec(symbol: str) -> TickerSpec | None:
    return BY_SYMBOL.get(symbol.upper()) or BY_SYMBOL.get(symbol)


def display_name(symbol: str) -> str:
    spec = _spec(symbol)
    return spec.name if spec else symbol.upper()


def market_for(symbol: str) -> str:
    """Which market a symbol trades in — decides currency formatting in the UI."""
    spec = _spec(symbol)
    if spec:
        return spec.market
    # Yahoo suffixes Korean listings; anything else is treated as US.
    return "KR" if symbol.upper().endswith((".KS", ".KQ")) else "US"


def sector_for(symbol: str) -> str:
    spec = _spec(symbol)
    return spec.sector if spec else "기타"
