"""Rate limiting and retries for provider calls (ARC-08 §4.5).

In-process token bucket. A Redis-backed shared limiter is needed only once more than one process
calls the same provider (ENG-05 §12 runs a single fetcher); the ``RateLimiter`` protocol allows it.
Backoff values are the ARC-08 §4.5 design placeholders (unverified, OQ-INT-01).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Protocol

from app.providers.base import ProviderRateLimited, ProviderUnavailable

BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)


class RateLimiter(Protocol):
    def acquire(self) -> None: ...


class TokenBucket:
    def __init__(
        self,
        rate_per_s: float,
        capacity: int | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_s <= 0:
            raise ValueError("rate must be positive")
        self._rate = rate_per_s
        self._capacity = float(capacity if capacity is not None else max(1, int(rate_per_s)))
        self._tokens = self._capacity
        self._clock, self._sleep = clock, sleep
        self._last = clock()

    def acquire(self) -> None:
        now = self._clock()
        self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._rate)
        self._last = now
        if self._tokens < 1:
            wait = (1 - self._tokens) / self._rate
            self._sleep(wait)
            self._last = self._clock()
            self._tokens = 1.0
        self._tokens -= 1


def call_with_retries[T](
    fn: Callable[[], T],
    sleep: Callable[[float], None] = time.sleep,
    delays: tuple[float, ...] = BACKOFF_SECONDS,
    jitter: Callable[[], float] = random.random,
) -> T:
    """Retry on ``ProviderRateLimited``/``ProviderUnavailable`` with exponential backoff and jitter.

    Auth and data errors propagate immediately.
    """
    for delay in delays:
        try:
            return fn()
        except (ProviderRateLimited, ProviderUnavailable):
            sleep(delay * (0.5 + jitter()))
    return fn()
