from datetime import datetime

from app.ingestion.session import IST, session_bar_starts
from app.providers import ProviderContext, ProviderInstrumentRef
from app.providers.demo import DemoProvider

CTX = ProviderContext("demo", lambda: "")
REF = ProviderInstrumentRef("1000", "DEMOA")
START, END = datetime(2026, 11, 17, 9, 0, tzinfo=IST), datetime(2026, 11, 17, 16, 0, tzinfo=IST)


def test_full_session_counts_and_grid() -> None:
    p = DemoProvider()
    five = p.fetch_bars(CTX, REF, "5m", START, END)
    fifteen = p.fetch_bars(CTX, REF, "15m", START, END)
    assert [b.bar_start for b in five] == session_bar_starts(START.date(), "5m")
    assert len(five) == 75 and len(fifteen) == 25


def test_deterministic_and_valid_ohlc() -> None:
    p = DemoProvider()
    a = p.fetch_bars(CTX, REF, "5m", START, END)
    assert a == p.fetch_bars(CTX, REF, "5m", START, END)
    assert all(b.low <= min(b.open, b.close) and b.high >= max(b.open, b.close) and b.volume > 0 for b in a)
    other = p.fetch_bars(CTX, ProviderInstrumentRef("1001", "DEMOB"), "5m", START, END)
    assert other != a


def test_15m_is_exact_aggregate_of_5m() -> None:
    p = DemoProvider()
    five = p.fetch_bars(CTX, REF, "5m", START, END)
    f = p.fetch_bars(CTX, REF, "15m", START, END)[0]
    g = five[:3]
    assert (f.open, f.close) == (g[0].open, g[2].close)
    assert f.high == max(b.high for b in g) and f.volume == sum(b.volume for b in g)


def test_weekend_has_no_bars_and_range_is_half_open() -> None:
    p = DemoProvider()
    sat = datetime(2026, 11, 21, 9, 0, tzinfo=IST)
    assert p.fetch_bars(CTX, REF, "5m", sat, sat.replace(hour=16)) == []
    cut = p.fetch_bars(CTX, REF, "5m", START, datetime(2026, 11, 17, 9, 30, tzinfo=IST))
    assert len(cut) == 3


def test_instruments_are_sample_flagged() -> None:
    ins = DemoProvider().fetch_instruments(CTX)
    assert len(ins) == 5 and all("sample" in i.name and i.segment == "DEMO" for i in ins)
