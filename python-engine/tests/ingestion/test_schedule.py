from datetime import datetime, time, timedelta

from app.ingestion.schedule import due_bars
from app.ingestion.session import IST

OPEN = datetime(2026, 11, 17, 9, 15, tzinfo=IST)
SESSION = (OPEN, datetime(2026, 11, 17, 15, 30, tzinfo=IST))


def at(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 11, 17, h, m, s, tzinfo=IST)


def test_nothing_before_the_first_close_or_on_a_non_trading_day() -> None:
    assert due_bars(at(9, 19), SESSION, {}) == []
    assert due_bars(at(11, 0), None, {}) == []


def test_first_close_makes_the_5m_bar_due() -> None:
    assert due_bars(at(9, 20), SESSION, {}) == [("5m", OPEN)]


def test_15m_follows_5m_on_a_shared_close() -> None:
    got = due_bars(at(9, 30), SESSION, {"5m": at(9, 20), "15m": None})
    assert got == [("5m", at(9, 25)), ("15m", OPEN)]


def test_only_bars_after_the_last_processed_are_due() -> None:
    got = due_bars(at(10, 0), SESSION, {"5m": at(9, 50), "15m": at(9, 30)})
    assert got == [("5m", at(9, 55)), ("15m", at(9, 45))]
    assert due_bars(at(10, 0), SESSION, {"5m": at(9, 55), "15m": at(9, 45)}) == []


def test_catchup_is_capped_to_the_most_recent_bars() -> None:
    got = [b for tf, b in due_bars(at(12, 0), SESSION, {}) if tf == "5m"]
    assert got == [at(11, 45), at(11, 50), at(11, 55)]


def test_no_bars_after_the_session_close() -> None:
    got = due_bars(at(18, 0), SESSION, {})
    assert max(b for _, b in got) == at(15, 25) and ("15m", at(15, 15)) in got
    assert all(b + timedelta(minutes=5) <= SESSION[1] for _, b in got)


def test_provider_cutoff_ends_the_schedule_at_15_15() -> None:
    got = due_bars(at(18, 0), SESSION, {}, provider_close=time(15, 15))
    assert max(b for tf, b in got if tf == "5m") == at(15, 10)
    assert max(b for tf, b in got if tf == "15m") == at(15, 0)
    assert (
        due_bars(at(15, 30), SESSION, {"5m": at(15, 10), "15m": at(15, 0)}, provider_close=time(15, 15)) == []
    )
