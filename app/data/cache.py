"""In-memory TTL cache.

The dashboard fans out to ~30 tickers per render. Without this, yfinance
rate-limits within a few page loads. Deliberately process-local — swap for Redis
if the app ever runs more than one worker.
"""

from __future__ import annotations

import functools
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_store: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def get(key: str) -> Any | None:
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            _store.pop(key, None)
            return None
        return value


def put(key: str, value: Any, ttl: float) -> None:
    with _lock:
        _store[key] = (time.monotonic() + ttl, value)


def clear() -> None:
    with _lock:
        _store.clear()


def ttl_cache(ttl: float, prefix: str = "") -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache a function's return value by its arguments for `ttl` seconds."""

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key = f"{prefix or fn.__qualname__}:{args!r}:{sorted(kwargs.items())!r}"
            hit = get(key)
            if hit is not None:
                return hit
            value = fn(*args, **kwargs)
            put(key, value, ttl)
            return value

        wrapper.cache_clear = clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
