"""News ingestion and sentiment scoring.

Ships with a lexicon scorer so the pipeline runs with zero API keys. The
`SentimentScorer` interface is the seam where an LLM-based scorer plugs in.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.models.schemas import NewsItem, NewsSummary

# Small finance-tuned lexicon. Crude, but transparent and dependency-free.
_POSITIVE = {
    "beat", "beats", "surge", "surged", "rally", "record", "upgrade", "upgraded",
    "outperform", "growth", "profit", "strong", "raises", "raised", "bullish",
    "expands", "wins", "approval", "breakthrough", "dividend",
}
_NEGATIVE = {
    "miss", "misses", "plunge", "plunged", "slump", "downgrade", "downgraded",
    "underperform", "loss", "losses", "weak", "cuts", "cut", "bearish", "lawsuit",
    "probe", "recall", "layoffs", "bankruptcy", "fraud", "warning",
}

_WORD = re.compile(r"[a-z']+")


class SentimentScorer(ABC):
    @abstractmethod
    def score(self, text: str) -> float:
        """Return sentiment in [-1, 1]."""


class LexiconSentimentScorer(SentimentScorer):
    def score(self, text: str) -> float:
        words = _WORD.findall(text.lower())
        if not words:
            return 0.0
        hits = sum(w in _POSITIVE for w in words) - sum(w in _NEGATIVE for w in words)
        matched = sum((w in _POSITIVE or w in _NEGATIVE) for w in words)
        if not matched:
            return 0.0
        return max(-1.0, min(1.0, hits / matched))


class NewsProvider(ABC):
    @abstractmethod
    def fetch(self, symbol: str, limit: int = 20) -> list[NewsItem]: ...


class YFinanceNewsProvider(NewsProvider):
    """Headlines attached to the ticker. No API key required."""

    def fetch(self, symbol: str, limit: int = 20) -> list[NewsItem]:
        import yfinance as yf

        raw = getattr(yf.Ticker(symbol.upper()), "news", []) or []
        items: list[NewsItem] = []

        for entry in raw[:limit]:
            content = entry.get("content", entry)
            headline = content.get("title") or entry.get("title")
            if not headline:
                continue
            published = entry.get("providerPublishTime")
            items.append(
                NewsItem(
                    symbol=symbol.upper(),
                    headline=headline,
                    url=(content.get("canonicalUrl") or {}).get("url") or entry.get("link"),
                    source=(content.get("provider") or {}).get("displayName")
                    or entry.get("publisher"),
                    published_at=(
                        datetime.fromtimestamp(published, tz=timezone.utc)
                        if published
                        else None
                    ),
                )
            )
        return items


def summarize_news(
    symbol: str,
    provider: NewsProvider,
    scorer: SentimentScorer | None = None,
    limit: int = 20,
) -> NewsSummary:
    scorer = scorer or LexiconSentimentScorer()
    items = provider.fetch(symbol, limit=limit)
    for item in items:
        item.sentiment = round(scorer.score(item.headline), 3)

    average = round(sum(i.sentiment for i in items) / len(items), 3) if items else 0.0
    return NewsSummary(
        symbol=symbol.upper(),
        item_count=len(items),
        average_sentiment=average,
        items=items,
    )
