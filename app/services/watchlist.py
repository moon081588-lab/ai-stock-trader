"""Watchlist persistence — the right-rail 관심 list."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.data.universe import display_name
from app.models.schemas import WatchlistEntry, WatchlistView

DEFAULT_SYMBOLS = ("000660.KS", "005930.KS", "NVDA", "AMD", "SOXL")


class WatchlistStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._symbols: list[str] = self._load()

    def _load(self) -> list[str]:
        if self.path.exists():
            return list(json.loads(self.path.read_text()))
        return list(DEFAULT_SYMBOLS)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._symbols, indent=2))

    def symbols(self) -> list[str]:
        return list(self._symbols)

    def add(self, symbol: str) -> list[str]:
        with self._lock:
            symbol = symbol.upper()
            if symbol not in self._symbols:
                self._symbols.append(symbol)
                self._save()
            return list(self._symbols)

    def remove(self, symbol: str) -> list[str]:
        with self._lock:
            self._symbols = [s for s in self._symbols if s != symbol.upper()]
            self._save()
            return list(self._symbols)


def build_view(symbols: list[str], snapshots: dict[str, dict]) -> WatchlistView:
    """Compose the rail. Symbols with no snapshot still render, just without a price."""
    entries = []
    for symbol in symbols:
        snap = snapshots.get(symbol)
        entries.append(
            WatchlistEntry(
                symbol=symbol,
                name=display_name(symbol),
                price=round(snap["price"], 2) if snap else None,
                change=round(snap["change"], 2) if snap else None,
                change_pct=round(snap["change_pct"], 2) if snap else None,
            )
        )
    return WatchlistView(entries=entries)
