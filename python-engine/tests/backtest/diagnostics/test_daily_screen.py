"""Daily screening protocol: the four detectors, filters and the family."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.backtest.diagnostics.daily import DayBar
from app.backtest.diagnostics.daily_screen import (
    FAMILY,
    STOP_MAX_PCT,
    STOP_MIN_PCT,
    Signal,
    detect,
    detect_b2,
    detect_c4,
    detect_f3,
    detect_p1,
    floor_tick,
    passes_stop_range,
    pivots,
    stop_below,
)

D = Decimal


def hlc(rows: list[tuple[float, float, float | None]]) -> list[DayBar]:
    """Daily bars from (high, low, close); the close defaults to the midpoint and is also the open."""
    out = []
    for i, (h, lo, c) in enumerate(rows):
        close = D(str(c if c is not None else (h + lo) / 2))
        out.append(DayBar(date(2024, 1, 1) + timedelta(days=i), close, D(str(h)), D(str(lo)), close))
    return out


# An uptrend with rising swing highs (112 at 6, 120 at 13) and rising swing lows (94 at 2, 99 at 9),
# then a pullback to a low of 106 (session 16) and a trigger on session 17.
TREND: list[tuple[float, float, float | None]] = [
    (100, 98, None), (99, 96, None), (98, 94, None), (101, 95, None), (104, 98, None), (108, 102, None),
    (112, 106, None), (110, 104, None), (108, 101, None), (105, 99, None), (107, 100, None), (110, 103, None),
    (115, 108, None), (120, 113, None), (118, 111, None), (116, 109, None), (113, 106, None), (119, 112, 115.5),
]  # fmt: skip


def test_pivots_use_the_intraday_tie_rule() -> None:
    bars = hlc(TREND)
    highs, lows = pivots(bars)
    assert highs == [6, 13] and lows == [2, 9]
    tie_right = hlc(
        [(10, 9, None), (11, 10, None), (12, 11, None), (12, 10, None), (11, 9, None), (10, 8, None)]
    )
    assert pivots(tie_right)[0] == [2]  # an equal high on the right still counts
    tie_left = hlc(
        [(12, 9, None), (11, 10, None), (12, 11, None), (11, 10, None), (10, 9, None), (9, 8, None)]
    )
    assert pivots(tie_left)[0] == []  # an equal high on the left does not


def test_p1_signals_the_first_close_above_the_prior_high_after_the_pullback() -> None:
    bars = hlc(TREND)
    (sig,) = detect_p1(bars, D(3))
    assert sig.index == 17 and sig.ref == D("115.5")
    assert sig.stop == stop_below(D(106)) == D("105.90")  # the pullback low
    assert 4 <= sig.stop_pct <= 10
    assert detect_p1(bars, D(6)) == [sig]  # the 11.7% pullback also clears the deeper gate
    assert detect_p1(bars, D(12)) == []  # but not 12%


def test_p1_needs_intact_structure_and_one_signal_per_swing_high() -> None:
    broken = [*TREND[:16], (113, 98, None), TREND[17]]  # the pullback low 98 breaks the latest swing low 99
    assert detect_p1(hlc(broken), D(3)) == []
    more = [*TREND, (121, 114, None), (126, 118, 122)]  # a later close above the prior high, same swing high
    assert len(detect_p1(hlc(more), D(3))) == 1


def test_p1_does_not_look_ahead() -> None:
    bars = hlc(TREND)
    full = detect_p1(bars, D(3))
    assert detect_p1(bars[:17], D(3)) == []  # before the trigger session closes there is no signal
    assert detect_p1(bars[:18], D(3)) == full  # later sessions never change it


def test_b2_first_close_above_the_range_high_with_the_20_session_low_stop() -> None:
    rows = [(10, 9, 9.5)] * 6 + [(10.6, 9.8, 10.5), (10.9, 10.4, 10.8)]
    sigs = detect_b2(hlc(rows), 5)
    assert [s.index for s in sigs] == [6]  # session 7 is the second close above, not a new breakout
    assert sigs[0].stop == stop_below(D(9)) == D("8.95")
    assert detect_b2(hlc(rows[:6]), 5) == []  # no close above yet
    again = [
        *rows,
        (9.5, 8.8, 9.0),
        (9.6, 8.9, 9.1),
        (9.7, 9.0, 9.2),
        (9.8, 9.1, 9.3),
        (9.9, 9.2, 9.4),
        (11.2, 10.0, 11.0),
    ]
    assert [s.index for s in detect_b2(hlc(again), 5)] == [6, 13]  # a fresh breakout later


def test_f3_breakdown_then_a_reclaim_within_three_sessions() -> None:
    base = [(10, 9, 9.5)] * 6
    ok = hlc([*base, (9.2, 8.7, 8.9), (9.0, 8.6, 8.8), (9.4, 8.9, 9.1)])  # breakdown 6, reclaim 8
    (sig,) = detect_f3(ok, 5)
    assert sig.index == 8 and sig.ref == D("9.1")
    assert sig.stop == stop_below(D("8.6")) == D("8.55")
    late = hlc(
        [*base, (9.2, 8.7, 8.9), (9.0, 8.6, 8.8), (9.0, 8.6, 8.7), (9.0, 8.6, 8.7), (9.4, 8.9, 9.1)]
    )  # fourth session
    assert detect_f3(late, 5) == []
    inside = hlc([*base, (9.2, 8.7, 8.9), (9.0, 8.6, 8.8), (9.0, 8.6, 8.7), (9.4, 8.9, 9.1)])  # third session
    assert [s.index for s in detect_f3(inside, 5)] == [9]


def test_f3_consecutive_breakdown_sessions_count_once() -> None:
    base = [(10, 9, 9.5)] * 6
    rows = hlc([*base, (9.2, 8.7, 8.9), (8.95, 8.6, 8.85), (9.4, 8.9, 9.1)])
    assert len(detect_f3(rows, 5)) == 1


def test_c4_needs_the_fall_and_a_close_in_the_top_third() -> None:
    rows = hlc([(101, 99, 100), (96, 92, 95)])  # a 5% fall, close 3 above a 4-wide range: top third
    (sig,) = detect_c4(rows, D(4))
    assert sig.index == 1 and sig.ref == D(95) and sig.stop == D("91.95")
    assert detect_c4(rows, D(6)) == []  # not a 6% fall
    weak = hlc([(101, 99, 100), (96, 92, 93)])  # closes in the lower third
    assert detect_c4(weak, D(4)) == []
    assert detect_c4(hlc([(101, 99, 100), (96, 96, 96)]), D(4)) == []  # a zero-range session


def test_stop_range_and_tick_and_family() -> None:
    def sig(pct: str) -> Signal:
        return Signal(1, D(100), D(100) * (1 - D(pct) / 100))

    assert (D(4), D(10)) == (STOP_MIN_PCT, STOP_MAX_PCT)
    assert passes_stop_range(sig("4")) and passes_stop_range(sig("10"))
    assert not passes_stop_range(sig("3.99")) and not passes_stop_range(sig("10.01"))
    assert floor_tick(D("105.947")) == D("105.90") and floor_tick(D("8.5957")) == D("8.55")
    assert [v.vid for v in FAMILY] == ["P1a", "P1b", "B2a", "B2b", "F3a", "F3b", "C4a", "C4b"]
    assert {v.idea for v in FAMILY} == {"P1", "B2", "F3", "C4"} and len(FAMILY) == 8


def test_detect_dispatches_by_idea() -> None:
    bars = hlc(TREND)
    assert detect(FAMILY[0], bars) == detect_p1(bars, D(3))
    assert detect(FAMILY[6], bars) == detect_c4(bars, D(4))
