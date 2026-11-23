"""Candle and volume screening protocol: patterns, volume filter, volume audit and the candle exit."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.backtest.costs import DeliverySchedule
from app.backtest.diagnostics.daily import DailyRules, DayBar, is_candle_exit, run_daily
from app.backtest.diagnostics.daily_candle import (
    FAMILY,
    at_support,
    detect_candle,
    high_volume,
    is_bullish_engulfing,
    is_doji,
    is_hammer,
    non_comparable_sessions,
    volume_level_shifts,
)
from app.backtest.diagnostics.daily_screen import stop_below

D = Decimal


def bars_of(rows: list[tuple[float, float, float, float, int]]) -> list[DayBar]:
    """Daily bars from (open, high, low, close, volume), on consecutive dates."""
    return [
        DayBar(date(2024, 1, 1) + timedelta(days=i), D(str(o)), D(str(h)), D(str(lo)), D(str(c)), v)
        for i, (o, h, lo, c, v) in enumerate(rows)
    ]


def one(o: float, h: float, lo: float, c: float, v: int = 100) -> DayBar:
    return bars_of([(o, h, lo, c, v)])[0]


FLAT = (10.0, 10.2, 9.8, 10.0, 100)


def test_hammer_needs_a_long_lower_wick_a_small_body_and_a_short_upper_wick() -> None:
    assert is_hammer(one(10.0, 10.1, 9.0, 10.05))  # lower 1.0 of 1.1, body 0.05, upper 0.05
    assert not is_hammer(one(10.0, 10.5, 9.0, 10.05))  # upper wick too long
    assert not is_hammer(one(9.2, 10.1, 9.0, 10.05))  # body above 30% of the range
    assert not is_hammer(one(10.0, 10.0, 10.0, 10.0))  # a zero range


def test_doji_and_engulfing() -> None:
    assert is_doji(one(10.0, 11.0, 9.0, 10.15)) and not is_doji(one(10.0, 11.0, 9.0, 10.3))
    red, green = one(10.2, 10.3, 9.9, 10.0), one(9.9, 10.4, 9.8, 10.3)
    assert is_bullish_engulfing(red, green)  # open 9.9 <= 10.0 and close 10.3 >= 10.2
    assert not is_bullish_engulfing(red, one(10.05, 10.4, 10.0, 10.3))  # opens above the previous close
    assert not is_bullish_engulfing(red, one(9.9, 10.3, 9.8, 10.1))  # does not cover the previous open
    assert not is_bullish_engulfing(green, green)  # the previous session is green


def test_support_context_and_volume_filter_boundaries() -> None:
    base = [(10.0, 10.5, 10.0, 10.2, 100)] * 21
    ok = bars_of([*base, (10.2, 10.3, 10.1, 10.2, 100)])  # low 10.1 = 1.01 x 10.0: allowed
    far = bars_of([*base, (10.2, 10.3, 10.12, 10.2, 100)])
    assert at_support(ok, 21) and not at_support(far, 21)
    assert not at_support(bars_of(base[:10]), 5)  # fewer than 20 sessions before
    vols = [(10.0, 10.2, 9.8, 10.0, 100)] * 20
    assert high_volume(bars_of([*vols, (10.0, 10.2, 9.8, 10.0, 150)]), 20)  # exactly 1.5 x
    assert not high_volume(bars_of([*vols, (10.0, 10.2, 9.8, 10.0, 149)]), 20)
    assert not high_volume(bars_of([(10.0, 10.2, 9.8, 10.0, 0)] * 20 + [FLAT]), 20)  # zero mean


def test_family_has_twelve_fixed_variants() -> None:
    assert [v.vid for v in FAMILY] == [
        "H-A", "H-AV", "H-S", "H-SV", "E-A", "E-AV", "E-S", "E-SV", "D-A", "D-AV", "D-S", "D-SV",
    ]  # fmt: skip
    assert len(FAMILY) == 12


def _hammer_series(volume: int = 100) -> list[DayBar]:
    # sessions 0-4 flat around 10, session 5 a hammer (low 9.0)
    return bars_of([FLAT] * 5 + [(10.0, 10.1, 9.0, 10.05, volume)])


def test_hammer_signal_uses_the_five_session_low_for_the_stop() -> None:
    (sig,) = detect_candle(FAMILY[0], _hammer_series())  # H-A
    assert sig.index == 5 and sig.ref == D("10.05")
    assert sig.stop == stop_below(D("9.0")) == D("8.95")
    assert detect_candle(FAMILY[2], _hammer_series()) == []  # H-S: fewer than 20 sessions of history


def test_hammer_at_support_with_and_without_volume() -> None:
    base = [(10.0, 10.5, 10.0, 10.2, 100)] * 21
    series = bars_of([*base, (10.1, 10.2, 9.05, 10.15, 100)])  # hammer; low 9.05 undercuts the 20-session low
    assert [s.index for s in detect_candle(FAMILY[2], series)] == [21]  # H-S
    assert detect_candle(FAMILY[3], series) == []  # H-SV: volume only 1.0x
    loud = bars_of([*base, (10.1, 10.2, 9.05, 10.15, 200)])
    assert [s.index for s in detect_candle(FAMILY[3], loud)] == [21]  # H-SV
    assert detect_candle(FAMILY[3], loud, bad_volume={21}) == []  # a non-comparable volume window


def test_engulfing_and_doji_signals() -> None:
    eng = bars_of([FLAT] * 4 + [(10.2, 10.3, 9.9, 10.0, 100), (9.9, 10.4, 9.8, 10.3, 100)])
    assert [s.index for s in detect_candle(FAMILY[4], eng)] == [5]  # E-A
    doji = bars_of([FLAT] * 4 + [(10.0, 10.5, 9.5, 10.05, 100), (10.0, 10.6, 9.9, 10.55, 100)])
    assert [s.index for s in detect_candle(FAMILY[8], doji)] == [5]  # D-A: green close above the doji's high
    below = bars_of([FLAT] * 4 + [(10.0, 10.5, 9.5, 10.05, 100), (10.0, 10.45, 9.9, 10.4, 100)])
    assert detect_candle(FAMILY[8], below) == []  # the close is not above the doji's high


def test_signals_do_not_look_ahead() -> None:
    series = _hammer_series()
    full = detect_candle(FAMILY[0], series)
    more = bars_of(
        [
            *[
                (o, h, lo, c, v)
                for o, h, lo, c, v in [
                    (float(b.open), float(b.high), float(b.low), float(b.close), b.volume) for b in series
                ]
            ],
            (9.0, 9.1, 8.0, 8.1, 100),
        ]
    )
    assert detect_candle(FAMILY[0], more[:6]) == full and detect_candle(FAMILY[0], more[:5]) == []


def test_volume_level_shifts_and_split_signature() -> None:
    doubled = [100] * 30 + [200] * 30  # an unadjusted 2:1 split leaves a level shift of 2
    (shift,) = volume_level_shifts(doubled)
    assert shift[0] == 30 and abs(shift[1] - 2.0) < 1e-9 and shift[2]
    other = [100] * 30 + [250] * 30  # a real change of 2.5x is flagged as a shift but is not split-like
    (s2,) = volume_level_shifts(other)
    assert not s2[2]
    assert volume_level_shifts([100] * 30 + [150] * 30) == []  # 1.5x is below the 1.8x threshold
    assert non_comparable_sessions([shift, s2]) == set(range(30, 51))


def test_candle_exit_closes_at_the_close_with_slippage() -> None:
    entry_ref, stop = D("10"), D("9")
    base = [FLAT, (10.0, 10.4, 9.95, 10.3, 100), (10.3, 10.6, 10.2, 10.5, 100)]  # fill session, a green one
    engulf = bars_of(
        [*base, (10.55, 10.6, 10.0, 10.2, 100), FLAT]
    )  # red, opens above 10.5, closes below 10.3
    t = run_daily(
        engulf, 0, "A", entry_ref, stop, None, 10, DailyRules(), DeliverySchedule(), candle_exit=True
    )
    assert t is not None and t.reason == "CANDLE_EXIT" and t.exit_day == engulf[3].day
    assert t.exit == engulf[3].close * D("0.9995")
    plain = run_daily(engulf, 0, "A", entry_ref, stop, None, 10, DailyRules(), DeliverySchedule())
    assert plain is not None and plain.reason == "END_OF_DATA"  # no candle exit without the flag
    lower = bars_of(
        [*base, (10.45, 10.6, 10.25, 10.4, 100), (10.4, 10.5, 10.3, 10.45, 100)]
    )  # red, not engulfing, above the low
    t2 = run_daily(
        lower, 0, "A", entry_ref, stop, None, 10, DailyRules(), DeliverySchedule(), candle_exit=True
    )
    assert t2 is not None and t2.reason == "END_OF_DATA"
    breach = bars_of([*base, (10.4, 10.5, 10.1, 10.15, 100), FLAT])  # closes below the previous low 10.2
    t3 = run_daily(
        breach, 0, "A", entry_ref, stop, None, 10, DailyRules(), DeliverySchedule(), candle_exit=True
    )
    assert t3 is not None and t3.reason == "CANDLE_EXIT"


def test_is_candle_exit_conditions() -> None:
    green = one(10.0, 10.6, 9.9, 10.5)
    assert is_candle_exit(green, one(10.55, 10.6, 9.9, 9.95))  # bearish engulfing: closes below the open 10.0
    assert not is_candle_exit(
        green, one(10.4, 10.5, 10.1, 10.3)
    )  # red but does not engulf, close above the low
    assert is_candle_exit(green, one(10.4, 10.5, 9.8, 9.85))  # a close below the previous low
    assert not is_candle_exit(one(10.5, 10.6, 9.9, 10.0), one(10.0, 10.3, 9.95, 10.2))  # a green session
