"""Current-price cache (ENG-05 §12 step 3).

Last traded prices of open positions and the watchlist, kept in Redis with a short TTL. They feed
live P&L and "distance to level" only: never written to ``candles``, never read by analysis.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.providers.base import ProviderContext, QuoteProvider

PRICE_TTL_S = 30  # HYPOTHESIS: a few polling intervals; stale prices must not look live


class PriceCache(Protocol):
    def set_many(self, source: str, prices: dict[str, Decimal]) -> None: ...
    def get(self, source: str, symbol: str) -> Decimal | None: ...


def _key(source: str, symbol: str) -> str:
    return f"px:{source}:{symbol}"


class RedisPriceCache:
    """``client`` is a redis-py client created with ``decode_responses=True``."""

    def __init__(self, client: RedisLike, ttl_s: int = PRICE_TTL_S) -> None:
        self._r, self._ttl = client, ttl_s

    def set_many(self, source: str, prices: dict[str, Decimal]) -> None:
        pipe = self._r.pipeline()
        for sym, px in prices.items():
            pipe.set(_key(source, sym), str(px), ex=self._ttl)
        pipe.execute()

    def get(self, source: str, symbol: str) -> Decimal | None:
        v = self._r.get(_key(source, symbol))
        return Decimal(v) if v is not None else None


class RedisLike(Protocol):
    def pipeline(self) -> PipeLike: ...
    def get(self, key: str) -> str | None: ...


class PipeLike(Protocol):
    def set(self, key: str, value: str, ex: int) -> object: ...
    def execute(self) -> object: ...


class InMemoryPriceCache:
    """Test/dev cache with the same TTL semantics, driven by an injectable clock."""

    def __init__(self, now: Callable[[], datetime], ttl_s: int = PRICE_TTL_S) -> None:
        self._now, self._ttl = now, ttl_s
        self._d: dict[str, tuple[Decimal, datetime]] = {}

    def set_many(self, source: str, prices: dict[str, Decimal]) -> None:
        t = self._now()
        for sym, px in prices.items():
            self._d[_key(source, sym)] = (px, t)

    def get(self, source: str, symbol: str) -> Decimal | None:
        hit = self._d.get(_key(source, symbol))
        if hit is None or (self._now() - hit[1]).total_seconds() > self._ttl:
            return None
        return hit[0]


def refresh_prices(
    provider: QuoteProvider, ctx: ProviderContext, cache: PriceCache, source: str, symbols: list[str]
) -> int:
    """Poll the provider for ``symbols`` and cache the results. Returns how many were cached.

    Provider errors propagate; the cached entries then simply expire (no stale price shown as live).
    """
    if not symbols:
        return 0
    prices = provider.fetch_ltp(ctx, symbols)
    cache.set_many(source, prices)
    return len(prices)
