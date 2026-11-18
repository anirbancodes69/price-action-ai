from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.ingestion.quality import check_aggregate, check_session_bars
from app.ingestion.session import IST, session_bar_starts
from app.providers import ProviderContext, ProviderInstrumentRef
from app.providers.demo import DemoProvider

DAY = date(2026, 11, 17)
S, E = datetime(2026, 11, 17, 9, 0, tzinfo=IST), datetime(2026, 11, 17, 16, 0, tzinfo=IST)
CTX, REF = ProviderContext("d", lambda: ""), ProviderInstrumentRef("1000", "DEMOA")
P = DemoProvider()
FIVE = P.fetch_bars(CTX, REF, "5m", S, E)
FIFTEEN = P.fetch_bars(CTX, REF, "15m", S, E)


def types(r) -> list[str]:
    return [i.type for i in r.issues]


def test_grid_counts() -> None:
    assert len(session_bar_starts(DAY, "5m")) == 75 and len(session_bar_starts(DAY, "15m")) == 25


def test_clean_session_has_no_issues() -> None:
    r = check_session_bars(DAY, "5m", FIVE)
    assert r.issues == [] and r.complete and len(r.accepted) == 75
    assert check_session_bars(DAY, "15m", FIFTEEN).issues == []


def test_missing_bar_is_reported_and_incomplete() -> None:
    r = check_session_bars(DAY, "5m", FIVE[:10] + FIVE[11:])
    assert types(r) == ["MISSING_BAR"] and r.issues[0].bar_start == FIVE[10].bar_start and not r.complete


def test_duplicate_keeps_last() -> None:
    later = replace(FIVE[3], close=FIVE[3].high)
    r = check_session_bars(DAY, "5m", [*FIVE, later])
    assert types(r) == ["DUPLICATE"] and r.accepted[3].close == FIVE[3].high


def test_misaligned_outside_and_invalid_are_rejected() -> None:
    bad_grid = replace(FIVE[0], bar_start=FIVE[0].bar_start + timedelta(minutes=2))
    outside = replace(FIVE[0], bar_start=FIVE[0].bar_start - timedelta(minutes=5))
    after = replace(FIVE[0], bar_start=FIVE[-1].bar_start + timedelta(minutes=5))
    bad_ohlc = replace(FIVE[1], high=FIVE[1].low - Decimal("1"))
    r = check_session_bars(DAY, "5m", [bad_grid, outside, after, bad_ohlc, *FIVE[2:]])
    got = types(r)
    assert got.count("MISALIGNED_BAR") == 1 and got.count("OUTSIDE_SESSION") == 2
    assert got.count("OHLC_INVALID") == 1 and got.count("MISSING_BAR") == 2  # FIVE[0], FIVE[1]


def test_special_session_grid_override() -> None:
    short = session_bar_starts(DAY, "5m")[:6]
    r = check_session_bars(DAY, "5m", FIVE[:6], expected=short)
    assert r.issues == []


def test_aggregate_ok_and_mismatch() -> None:
    assert check_aggregate(FIVE, FIFTEEN) == []
    broken = [replace(FIFTEEN[2], high=FIFTEEN[2].high + Decimal("5")), *FIFTEEN[3:]]
    assert [i.type for i in check_aggregate(FIVE, broken)] == ["AGGREGATE_MISMATCH"]
    skew = replace(FIFTEEN[0], volume=FIFTEEN[0].volume * 2)
    assert len(check_aggregate(FIVE, [skew])) == 1
    near = replace(FIFTEEN[0], volume=FIFTEEN[0].volume + 1)  # within 1%
    assert check_aggregate(FIVE, [near]) == []
    assert check_aggregate(FIVE[1:], FIFTEEN[:1]) == []  # incomplete group is skipped


def test_kite_cutoff_grid_is_72_and_24_bars() -> None:
    cut = time(15, 15)
    five, fifteen = session_bar_starts(DAY, "5m", cut), session_bar_starts(DAY, "15m", cut)
    assert (len(five), five[-1].strftime("%H:%M")) == (72, "15:10")
    assert (len(fifteen), fifteen[-1].strftime("%H:%M")) == (24, "15:00")


def test_cutoff_session_is_complete_without_the_last_bars_and_rejects_later_ones() -> None:
    cut = time(15, 15)
    r = check_session_bars(DAY, "5m", FIVE[:72], close=cut)
    assert r.issues == [] and r.complete and len(r.accepted) == 72
    late = check_session_bars(DAY, "5m", FIVE, close=cut)
    assert [i.type for i in late.issues] == ["OUTSIDE_SESSION"] * 3 and len(late.accepted) == 72
