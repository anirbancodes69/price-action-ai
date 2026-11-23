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


# --- Phase 1 P1: live monitor and backtest share one exit rule (exit-execution-specification.md) ---


def test_p1_gap_up_through_the_target_with_a_low_below_the_stop_is_a_target_not_a_stop() -> None:
    """Audit finding P1-a: the monitor used to test `low <= stop` first and report STOP; the backtest says TARGET_GAP."""
    s = sig({3: ("104", "105", "98", "100")})
    assert (s.reason, s.bar_end) == ("TARGET", OPEN + timedelta(minutes=20))


def test_p1_gap_down_through_the_stop_with_a_high_above_the_target_is_a_stop() -> None:
    assert sig({3: ("98", "104", "97", "100")}).reason == "STOP"


def test_p1_a_bar_starting_at_the_session_exit_time_is_session_end_even_if_it_touches_the_stop() -> None:
    """Audit finding P1-b: the backtest exits at the open of that bar; the monitor used to report STOP."""
    exit_time = OPEN + timedelta(minutes=15)  # bar 3 starts here
    s = sig({3: ("100", "100.5", "98", "99")}, session_exit_time=exit_time)
    assert (s.reason, s.bar_end) == ("SESSION_END", exit_time)


def test_p1_a_missing_stop_or_target_is_never_hit() -> None:
    assert sig({3: ("100", "110", "90", "100")}, stop=None, target=None).signal == "HOLD"
    assert sig({3: ("100", "110", "90", "100")}, stop=None).reason == "TARGET"


def test_p1_monitor_and_step_position_agree_on_the_exit_reason_bar_by_bar() -> None:
    """Property check over a grid of bars: same exit or no exit, same reason family, same bar."""
    from app.backtest.trade import ExitConfig, Position, step_position

    stop, target = D("99"), D("103")
    exit_time = OPEN + timedelta(minutes=30)
    cfg = ExitConfig(D("0.05"), exit_time, True, False)
    grid = [D(x) for x in ("97", "98.5", "99", "100", "102.9", "103", "104")]
    for o in grid:
        for h in grid:
            for lo in grid:
                for c in grid:
                    if not (lo <= min(o, c) and h >= max(o, c)):
                        continue
                    b = bars({3: (str(o), str(h), str(lo), str(c))})
                    pos = Position("X", "T", 0, "", 1, D("100"), stop, target, ENTRY, ENTRY)
                    ex = step_position(pos, b[3], cfg)
                    m = monitor_position(
                        b[:4], ENTRY + timedelta(minutes=5), stop, target, session_exit_time=exit_time
                    )
                    if ex is None:
                        assert m.signal == "HOLD", (o, h, lo, c)
                    else:
                        assert m.signal == "EXIT" and ex[1].split("_")[0] == m.reason, (o, h, lo, c, ex, m)
