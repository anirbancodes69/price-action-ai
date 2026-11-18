from datetime import datetime, timedelta

import pytest

from app.ingestion.fetcher import InMemoryBarStore, run_bar_close
from app.ingestion.session import IST
from app.providers import (
    ProviderAuthExpired,
    ProviderBar,
    ProviderContext,
    ProviderInstrumentRef,
    ProviderUnavailable,
)
from app.providers.demo import DemoProvider

CTX = ProviderContext("d", lambda: "")
REFS = [ProviderInstrumentRef("1000", "DEMOA"), ProviderInstrumentRef("1001", "DEMOB")]
BAR = datetime(2026, 11, 17, 10, 0, tzinfo=IST)


class FakeTime:
    def __init__(self, start: datetime) -> None:
        self.t = start

    def now(self) -> datetime:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += timedelta(seconds=s)


def test_happy_path_stores_one_bar_per_instrument_and_is_idempotent() -> None:
    clk, store = FakeTime(BAR + timedelta(minutes=5)), InMemoryBarStore()
    rep = run_bar_close(DemoProvider(), CTX, store, REFS, "5m", BAR, clk.now, clk.sleep)
    assert rep.status == "COMPLETED" and rep.issues == []
    assert all(len(v) == 1 and BAR in v for v in store.bars.values())
    run_bar_close(DemoProvider(), CTX, store, REFS, "5m", BAR, clk.now, clk.sleep)
    assert all(len(v) == 1 for v in store.bars.values())


def test_forming_bar_is_refused() -> None:
    clk = FakeTime(BAR + timedelta(minutes=4))
    with pytest.raises(ValueError, match="not closed"):
        run_bar_close(DemoProvider(), CTX, InMemoryBarStore(), REFS, "5m", BAR, clk.now, clk.sleep)


class Flaky(DemoProvider):
    """Returns nothing for DEMOB until ``ready_after`` polls; DEMOA is always there."""

    def __init__(self, ready_after: int | None) -> None:
        self.ready_after, self.polls = ready_after, 0

    def fetch_bars(self, ctx, ref, timeframe, start, end):  # type: ignore[no-untyped-def]
        if ref.symbol == "DEMOB":
            self.polls += 1
            if self.ready_after is None or self.polls <= self.ready_after:
                return []
        return super().fetch_bars(ctx, ref, timeframe, start, end)


def test_late_bar_is_polled_then_stored() -> None:
    clk, store = FakeTime(BAR + timedelta(minutes=5)), InMemoryBarStore()
    rep = run_bar_close(Flaky(2), CTX, store, REFS, "5m", BAR, clk.now, clk.sleep)
    assert rep.status == "COMPLETED" and ("DEMOB", "5m") in store.bars


def test_bar_never_arrives_is_late_bar_and_partial() -> None:
    clk, store = FakeTime(BAR + timedelta(minutes=5)), InMemoryBarStore()
    rep = run_bar_close(Flaky(None), CTX, store, REFS, "5m", BAR, clk.now, clk.sleep)
    assert rep.status == "PARTIAL" and [i.type for i in rep.issues] == ["LATE_BAR"]
    assert ("DEMOB", "5m") not in store.bars
    assert clk.now() >= BAR + timedelta(minutes=10)  # polled until the next bar close


class Broken(DemoProvider):
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def fetch_bars(self, ctx, ref, timeframe, start, end) -> list[ProviderBar]:  # type: ignore[no-untyped-def]
        raise self.exc


def test_auth_expired_aborts_the_run() -> None:
    clk = FakeTime(BAR + timedelta(minutes=5))
    rep = run_bar_close(
        Broken(ProviderAuthExpired("x")), CTX, InMemoryBarStore(), REFS, "5m", BAR, clk.now, clk.sleep
    )
    assert rep.status == "FAILED" and rep.error_code == "PROVIDER_AUTH_EXPIRED"


def test_provider_outage_fails_all_instruments() -> None:
    clk = FakeTime(BAR + timedelta(minutes=5))
    rep = run_bar_close(
        Broken(ProviderUnavailable("x")), CTX, InMemoryBarStore(), REFS, "5m", BAR, clk.now, clk.sleep
    )
    assert rep.status == "FAILED" and all(o.error == "ProviderUnavailable" for o in rep.outcomes)
