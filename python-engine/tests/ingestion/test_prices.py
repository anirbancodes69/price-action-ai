from datetime import datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from app.ingestion.prices import InMemoryPriceCache, RedisPriceCache, refresh_prices
from app.ingestion.session import IST
from app.providers import ProviderAuthExpired, ProviderContext, ProviderDataError
from app.providers.demo import DemoProvider
from app.providers.kite import KiteProvider

CTX = ProviderContext("d", lambda: "tok")


class NoLimit:
    def acquire(self) -> None:
        return None


def kite(handler) -> KiteProvider:  # type: ignore[no-untyped-def]
    client = httpx.Client(base_url="https://api.kite.trade", transport=httpx.MockTransport(handler))
    return KiteProvider("K", client, limiter=NoLimit(), sleep=lambda s: None)


def test_kite_ltp_parses_and_sends_repeated_params() -> None:
    seen: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["i"] = req.url.params.get_list("i")
        return httpx.Response(
            200,
            json={
                "data": {
                    "NSE:RELIANCE": {"instrument_token": 1, "last_price": 2501.456},
                    "NSE:INFY": {"instrument_token": 2, "last_price": 1500},
                }
            },
        )

    out = kite(handler).fetch_ltp(CTX, ["RELIANCE", "INFY"])
    assert seen["i"] == ["NSE:RELIANCE", "NSE:INFY"]
    assert out == {"RELIANCE": Decimal("2501.46"), "INFY": Decimal("1500.00")}


def test_kite_ltp_chunks_and_normalises_errors() -> None:
    calls: list[int] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(len(req.url.params.get_list("i")))
        return httpx.Response(200, json={"data": {}})

    kite(handler).fetch_ltp(CTX, [f"S{i}" for i in range(450)])
    assert calls == [200, 200, 50]
    with pytest.raises(ProviderAuthExpired):
        kite(lambda r: httpx.Response(403)).fetch_ltp(CTX, ["A"])
    with pytest.raises(ProviderDataError):
        kite(lambda r: httpx.Response(200, json={"data": {"NSE:A": {}}})).fetch_ltp(CTX, ["A"])


def test_cache_ttl_and_refresh_with_demo_provider() -> None:
    t = {"now": datetime(2026, 11, 17, 10, 0, tzinfo=IST)}
    cache = InMemoryPriceCache(lambda: t["now"], ttl_s=30)
    assert refresh_prices(DemoProvider(), CTX, cache, "demo", ["DEMOA", "DEMOB"]) == 2
    px = cache.get("demo", "DEMOA")
    assert px is not None and px > 0
    assert cache.get("demo", "NOPE") is None and cache.get("other", "DEMOA") is None
    t["now"] += timedelta(seconds=31)
    assert cache.get("demo", "DEMOA") is None  # expired, never shown as live
    assert refresh_prices(DemoProvider(), CTX, cache, "demo", []) == 0


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, tuple[str, int]] = {}

    def pipeline(self) -> "FakeRedis":
        return self

    def set(self, key: str, value: str, ex: int) -> object:
        self.data[key] = (value, ex)
        return None

    def execute(self) -> object:
        return None

    def get(self, key: str) -> str | None:
        return self.data[key][0] if key in self.data else None


def test_redis_cache_sets_ttl_and_namespaced_keys() -> None:
    r = FakeRedis()
    c = RedisPriceCache(r, ttl_s=30)
    c.set_many("src", {"RELIANCE": Decimal("2500.10")})
    assert r.data == {"px:src:RELIANCE": ("2500.10", 30)}
    assert c.get("src", "RELIANCE") == Decimal("2500.10") and c.get("src", "X") is None
