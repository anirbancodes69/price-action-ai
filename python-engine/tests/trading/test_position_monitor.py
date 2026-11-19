"""TV-MON: HOLD or EXIT on an open long position from closed 5m bars (TRD-07 §7.1). Hand-computed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.domain.risk.monitor import monitor_position
from app.domain.types import Bar

OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST
FLAT = ("100", "100.5", "99.5", "100")


def bars(overrides: dict[int, tuple[str, str, str, str]] | None = None, n: int = 6) -> list[Bar]:
    rows = overrides or {}
    out = []
    for i in range(n):
        o, h, lo, c = rows.get(i, FLAT)
        s = OPEN + timedelta(minutes=5 * i)
        out.append(Bar(s, s + timedelta(minutes=5), D(o), D(h), D(lo), D(c)))
    return out


ENTRY = OPEN + timedelta(minutes=10)  # the bar starting at index 2
STOP, TARGET = D("99"), D("103")


def sig(rows: dict[int, tuple[str, str, str, str]] | None = None, **kw):  # type: ignore[no-untyped-def]
    args = {"stop": STOP, "target": TARGET} | kw
    return monitor_position(bars(rows), ENTRY, **args)


def test_tv_mon_01_no_exit_condition_is_hold() -> None:
    s = sig()
    assert (s.signal, s.reason, s.bar_end) == ("HOLD", None, None)


def test_tv_mon_02_a_low_at_or_below_the_stop_is_a_stop_exit_at_that_bar() -> None:
    s = sig({4: ("100", "100.5", "99", "99.4")})  # low == stop counts
    assert (s.signal, s.reason, s.bar_end) == ("EXIT", "STOP", OPEN + timedelta(minutes=25))


def test_tv_mon_03_a_high_at_or_above_the_target_is_a_target_exit() -> None:
    s = sig({3: ("100", "103", "99.5", "102.5")})
    assert (s.signal, s.reason, s.bar_end) == ("EXIT", "TARGET", OPEN + timedelta(minutes=20))


def test_tv_mon_04_stop_and_target_in_one_bar_the_stop_wins() -> None:
    s = sig({3: ("100", "104", "98", "100")})
    assert s.reason == "STOP"


def test_tv_mon_05_bars_before_the_entry_bar_are_ignored() -> None:
    # bar 1 started before the entry and breached the stop; bar 2 (the entry bar) starts at the fill
    assert sig({1: ("100", "100.5", "90", "95")}).signal == "HOLD"
    assert sig({2: ("100", "100.5", "90", "95")}).reason == "STOP"


def test_tv_mon_06_the_first_condition_in_time_order_wins() -> None:
    s = sig({3: ("100", "103.5", "99.5", "103")}, structure_exit_bars=frozenset({4}))
    assert s.reason == "TARGET"
    s = sig({4: ("100", "103.5", "99.5", "103")}, structure_exit_bars=frozenset({3}))
    assert s.reason == "STRUCTURE_EXIT" and s.bar_end == OPEN + timedelta(minutes=20)


def test_tv_mon_07_a_bearish_choch_after_entry_is_a_structure_exit() -> None:
    s = sig(structure_exit_bars=frozenset({3}))
    assert (s.signal, s.reason, s.bar_end) == ("EXIT", "STRUCTURE_EXIT", OPEN + timedelta(minutes=20))
    assert sig(structure_exit_bars=frozenset({1})).signal == "HOLD"  # before the entry
    assert sig(structure_exit_bars=frozenset({3}), structure_exit_enabled=False).signal == "HOLD"


def test_tv_mon_08_session_end_applies_from_the_exit_time() -> None:
    last_end = OPEN + timedelta(minutes=30)
    assert sig(session_exit_time=last_end + timedelta(minutes=5)).signal == "HOLD"
    s = sig(session_exit_time=last_end)
    assert (s.signal, s.reason, s.bar_end) == ("EXIT", "SESSION_END", last_end)
    assert sig(session_exit_time=last_end, session_exit_enabled=False).signal == "HOLD"


def test_tv_mon_09_a_missing_stop_or_target_is_never_hit() -> None:
    crash = {4: ("100", "100.5", "50", "60")}
    assert sig(crash, stop=None).signal == "HOLD"
    assert sig({4: ("100", "200", "99.5", "150")}, target=None).signal == "HOLD"
    assert monitor_position([], ENTRY, STOP, TARGET).signal == "HOLD"  # no bars yet
