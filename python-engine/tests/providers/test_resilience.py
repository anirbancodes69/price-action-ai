from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.providers import (
    ProviderAuthExpired,
    ProviderContext,
    ProviderInstrumentRef,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.providers.kite import KiteProvider
from app.providers.resilience import TokenBucket, call_with_retries

IST = ZoneInfo("Asia/Kolkata")
CTX, REF = ProviderContext("d", lambda: "tok"), ProviderInstrumentRef("1", "X")
T0, T1 = datetime(2026, 11, 17, 9, 15, tzinfo=IST), datetime(2026, 11, 17, 9, 20, tzinfo=IST)
OK = {"data": {"candles": [["2026-11-17T09:15:00+0530", 1, 2, 1, 2, 3]]}}


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.now += s


def test_token_bucket_spaces_requests() -> None:
    c = Clock()
    b = TokenBucket(2.0, capacity=2, clock=c.time, sleep=c.sleep)
    for _ in range(4):
        b.acquire()
    assert c.slept == [0.5, 0.5]  # burst of 2, then one per 0.5 s
    assert c.now == pytest.approx(1.0)


def test_retries_then_succeeds_with_backoff() -> None:
    calls = {"n": 0}
    slept: list[float] = []

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderRateLimited("x")
        return "ok"

    assert call_with_retries(fn, sleep=slept.append, jitter=lambda: 0.5) == "ok"
    assert slept == [1.0, 2.0]


def test_gives_up_after_all_delays_and_never_retries_auth() -> None:
    n = {"c": 0}

    def down() -> None:
        n["c"] += 1
        raise ProviderUnavailable("x")

    with pytest.raises(ProviderUnavailable):
        call_with_retries(down, sleep=lambda s: None)
    assert n["c"] == 5  # first try + 4 retries

    def auth() -> None:
        n["c"] += 1
        raise ProviderAuthExpired("x")

    n["c"] = 0
    with pytest.raises(ProviderAuthExpired):
        call_with_retries(auth, sleep=lambda s: None)
    assert n["c"] == 1


def test_kite_retries_a_429_then_succeeds() -> None:
    codes = iter([429, 503, 200])

    def handler(req: httpx.Request) -> httpx.Response:
        code = next(codes)
        return httpx.Response(code, json=OK) if code == 200 else httpx.Response(code)

    client = httpx.Client(base_url="https://api.kite.trade", transport=httpx.MockTransport(handler))
    p = KiteProvider("K", client, sleep=lambda s: None)
    assert len(p.fetch_bars(CTX, REF, "5m", T0, T1)) == 1
