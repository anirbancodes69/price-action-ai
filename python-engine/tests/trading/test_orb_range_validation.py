"""E3 (OD-8 step 1): `ORB-MG-02` strict opening-range validation, ORB specification §7.1.2.

Vectors OR-V-xx follow the TRD-08 style: one named input, one exact expected result. The validator is pure;
these tests also prove determinism, input immutability and the absence of look-ahead. No test reads a database
or a stored candle.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.setups.orb_range import OrbRange, OrbRangeReason, validate_opening_range
from app.domain.types import Bar

D = Decimal
R = OrbRangeReason
OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST
SATURDAY_OPEN = datetime(
    2025, 2, 1, 3, 45, tzinfo=UTC
)  # a full-length Saturday session (Budget day 2025-02-01)


def bar(
    minute: int,
    o: str = "100",
    h: str = "101",
    low: str = "99",
    c: str = "100.5",
    *,
    open_: datetime = OPEN,
    length: int = 5,
) -> Bar:
    s = open_ + timedelta(minutes=minute)
    return Bar(s, s + timedelta(minutes=length), D(o), D(h), D(low), D(c))


def good(open_: datetime = OPEN) -> list[Bar]:
    return [
        bar(0, "100", "101", "99", "100.5", open_=open_),
        bar(5, "100.5", "102", "100", "101", open_=open_),
        bar(10, "101", "101.5", "98.5", "99.5", open_=open_),
        bar(15, "99.5", "100", "99", "99.8", open_=open_),  # the first bar after the range
    ]


def test_or_v_01_valid_range_wick_basis() -> None:
    r = validate_opening_range(good(), OPEN)
    assert r.valid and r.reason is None and r.reasons == ()
    assert (r.or_high, r.or_low) == (D("102"), D("98.5"))  # max high, min low over the three bars
    assert r.t_or == OPEN + timedelta(minutes=15) and r.bars_in_window == 3 and r.tick_checked is False


def test_or_v_02_result_does_not_depend_on_input_order() -> None:
    bars = good()
    assert validate_opening_range(list(reversed(bars)), OPEN) == validate_opening_range(bars, OPEN)


def test_or_v_03_bars_after_the_range_do_not_change_the_result() -> None:
    base = validate_opening_range([*good()[:3], bar(15)], OPEN)
    more = validate_opening_range([*good(), bar(20, h="500", low="1"), bar(25, h="900", low="0.5")], OPEN)
    assert base == more and more.valid


def test_or_v_04_bar_starting_at_t_or_is_outside_the_window_and_bar_ending_at_t_or_is_inside() -> None:
    r = validate_opening_range(good(), OPEN)
    assert r.bars_in_window == 3
    assert not any(b.start == OPEN + timedelta(minutes=15) for b in good()[:3])


@pytest.mark.parametrize("minutes,k", [(5, 1), (10, 2), (30, 6)])
def test_or_v_05_other_range_lengths_follow_k_equals_n_over_5(minutes: int, k: int) -> None:
    bars = [bar(5 * i) for i in range(k + 1)]
    r = validate_opening_range(bars, OPEN, minutes)
    assert r.valid and r.bars_in_window == k and r.t_or == OPEN + timedelta(minutes=minutes)
    assert not validate_opening_range(bars[: k - 1] + bars[k:], OPEN, minutes).valid if k > 1 else True


@pytest.mark.parametrize("minutes", [0, -5, 7, 12])
def test_or_v_06_invalid_range_length_is_rejected(minutes: int) -> None:
    with pytest.raises(ValueError, match="multiple of 5"):
        validate_opening_range(good(), OPEN, minutes)


# --- count and grid -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("missing", [0, 5, 10])
def test_or_v_10_a_missing_bar_anywhere_in_the_window_is_or_missing_bar(missing: int) -> None:
    bars = [b for b in good() if b.start != OPEN + timedelta(minutes=missing)]
    bars.append(bar(20))  # later data exists, so the series reaches t_OR and this is a gap, not "not closed"
    r = validate_opening_range(bars, OPEN)
    assert not r.valid and r.reason is R.OR_MISSING_BAR and r.reasons == (R.OR_MISSING_BAR,)
    assert r.or_high is None and r.or_low is None  # no fallback to the bars that exist


def test_or_v_11_known_gap_pattern_2024_06_25_first_bar_rejected_by_the_provider() -> None:
    bars = [bar(5), bar(10), bar(15), bar(20)]  # 09:15 absent
    assert validate_opening_range(bars, OPEN).reason is R.OR_MISSING_BAR


def test_or_v_12_known_gap_pattern_2025_01_06_opening_bar_then_nothing_until_09_35() -> None:
    bars = [bar(0), bar(20), bar(25)]  # 09:15, then 09:35, 09:40 (the 09:20-09:30 bars are absent)
    r = validate_opening_range(bars, OPEN)
    assert r.reason is R.OR_MISSING_BAR and r.bars_in_window == 1


def test_or_v_13_an_off_grid_start_time_does_not_fill_a_grid_slot() -> None:
    bars = [bar(0), bar(5), bar(6), bar(15)]  # 09:21 instead of 09:25
    r = validate_opening_range(bars, OPEN)
    assert r.reasons == (R.OR_MISSING_BAR,)


def test_or_v_14_a_repeated_start_time_is_or_duplicate_bar() -> None:
    bars = [bar(0), bar(5), bar(5, h="103"), bar(10), bar(15)]
    r = validate_opening_range(bars, OPEN)
    assert not r.valid and r.reasons == (R.OR_DUPLICATE_BAR,)


def test_or_v_15_more_than_k_bars_in_the_window_is_or_duplicate_bar() -> None:
    bars = [bar(0), bar(1), bar(5), bar(10), bar(15)]  # an extra off-grid bar 09:16-09:21 inside the window
    r = validate_opening_range(bars, OPEN)
    assert r.reasons == (R.OR_DUPLICATE_BAR,)


def test_or_v_16_duplicate_plus_gap_reports_both_with_missing_first() -> None:
    bars = [
        bar(0),
        bar(5),
        bar(5, h="103"),
        bar(15),
    ]  # three starts in the window, 09:25 absent, 09:20 repeated
    r = validate_opening_range(bars, OPEN)
    assert r.reasons == (R.OR_MISSING_BAR, R.OR_DUPLICATE_BAR) and r.reason is R.OR_MISSING_BAR


# --- closed ---------------------------------------------------------------------------------------------------------


def test_or_v_20_empty_series_is_not_closed() -> None:
    r = validate_opening_range([], OPEN)
    assert not r.valid and r.reasons == (R.OR_NOT_CLOSED,) and r.bars_in_window == 0


def test_or_v_21_series_that_has_not_reached_t_or_is_not_closed_and_nothing_else_is_judged() -> None:
    r = validate_opening_range(good()[:2], OPEN)  # evaluated at 09:25, the range closes at 09:30
    assert r.reasons == (R.OR_NOT_CLOSED,) and r.or_high is None


def test_or_v_22_a_bar_that_ends_after_t_or_is_not_closed() -> None:
    bars = [bar(0), bar(5), bar(10, length=10)]  # the last range bar ends at 09:35
    assert validate_opening_range(bars, OPEN).reason is R.OR_NOT_CLOSED


def test_or_v_23_a_fifteen_minute_bar_is_not_a_five_minute_range_bar() -> None:
    bars = [bar(0, length=15), bar(15)]
    r = validate_opening_range(bars, OPEN)
    assert R.OR_NOT_CLOSED in r.reasons and R.OR_MISSING_BAR in r.reasons


# --- valid OHLC and the tick ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "o,h,low,c",
    [
        ("100", "100.2", "99", "100.5"),  # high below close
        ("100", "101", "100.2", "100.5"),  # low above open
        ("100", "99", "100", "100"),  # high below low
        ("0", "1", "0", "1"),  # zero price
        ("-1", "1", "-2", "0.5"),  # negative price
        ("NaN", "101", "99", "100"),
        ("100", "Infinity", "99", "100"),
    ],
)
def test_or_v_30_invalid_ohlc_is_rejected(o: str, h: str, low: str, c: str) -> None:
    bars = [bar(0), bar(5, o, h, low, c), bar(10), bar(15)]
    r = validate_opening_range(bars, OPEN)
    assert not r.valid and r.reasons == (R.OR_INVALID_OHLC,)


def test_or_v_31_a_flat_bar_with_all_prices_equal_is_valid() -> None:
    bars = [bar(0, "100", "100", "100", "100"), bar(5), bar(10), bar(15)]
    assert validate_opening_range(bars, OPEN).valid


def test_or_v_32_without_a_tick_no_tick_check_is_made_and_the_result_says_so() -> None:
    adjusted = [
        bar(0, "24.318", "24.5", "24.1", "24.2"),
        bar(5, "24.2", "24.9", "24.0", "24.7"),
        bar(10),
        bar(15),
    ]
    # Prices of a provider-adjusted session need not sit on any tick grid: not a failure when no tick is supplied.
    r = validate_opening_range(adjusted, OPEN)
    assert r.valid and r.tick_checked is False


def test_or_v_33_there_is_no_default_tick() -> None:
    sig = inspect.signature(validate_opening_range)
    assert sig.parameters["tick"].default is None


def test_or_v_34_with_a_tick_every_price_of_the_window_must_be_a_multiple() -> None:
    ok = [bar(0, "100.05", "101.00", "99.00", "100.50"), bar(5), bar(10), bar(15)]
    r = validate_opening_range(ok, OPEN, tick=D("0.05"))
    assert r.valid and r.tick_checked is True
    off = [bar(0, "100.03", "101.00", "99.00", "100.50"), bar(5), bar(10), bar(15)]
    r2 = validate_opening_range(off, OPEN, tick=D("0.05"))
    assert r2.reasons == (R.OR_INVALID_OHLC,) and r2.tick_checked is True


def test_or_v_35_the_tick_is_taken_literally_a_0_05_grid_price_fails_a_0_10_tick() -> None:
    bars = [bar(0, "100.05", "101.00", "99.00", "100.50"), bar(5), bar(10), bar(15)]
    assert validate_opening_range(bars, OPEN, tick=D("0.10")).reasons == (R.OR_INVALID_OHLC,)
    assert validate_opening_range(bars, OPEN, tick=D("0.05")).valid


@pytest.mark.parametrize("tick", [D("0"), D("-0.05"), D("NaN"), D("Infinity")])
def test_or_v_36_an_unusable_tick_is_rejected_not_ignored(tick: Decimal) -> None:
    with pytest.raises(ValueError, match="tick"):
        validate_opening_range(good(), OPEN, tick=tick)


def test_or_v_37_prices_outside_the_range_window_are_not_checked_against_the_tick() -> None:
    bars = [*good()[:3], bar(15, "100.03", "100.07", "99.99", "100.01")]
    assert validate_opening_range(bars, OPEN, tick=D("0.01")).valid


def test_or_v_38_a_uniformly_scaled_session_keeps_its_range_ratios() -> None:
    scaled = [Bar(b.start, b.end, b.open / 2, b.high / 2, b.low / 2, b.close / 2) for b in good()]
    a, b = validate_opening_range(good(), OPEN), validate_opening_range(scaled, OPEN)
    assert a.valid and b.valid and b.or_high == a.or_high / 2 and b.or_low == a.or_low / 2  # type: ignore[operator]


# --- session --------------------------------------------------------------------------------------------------------


def test_or_v_40_an_excluded_session_is_session_excluded_even_with_perfect_bars() -> None:
    r = validate_opening_range(good(), OPEN, session_excluded=True)
    assert not r.valid and r.reasons == (R.SESSION_EXCLUDED,) and r.or_high is None


def test_or_v_41_session_exclusion_is_last_in_the_precedence_order() -> None:
    bars = [bar(5), bar(10), bar(15)]
    r = validate_opening_range(bars, OPEN, session_excluded=True)
    assert r.reasons == (R.OR_MISSING_BAR, R.SESSION_EXCLUDED) and r.reason is R.OR_MISSING_BAR


def test_or_v_42_a_full_length_saturday_session_is_valid_it_is_not_excluded_for_being_a_weekend() -> None:
    assert SATURDAY_OPEN.weekday() == 5
    r = validate_opening_range(good(SATURDAY_OPEN), SATURDAY_OPEN)
    assert r.valid


# --- determinism, immutability, no look-ahead -----------------------------------------------------------------------


def test_or_v_50_deterministic_and_the_input_is_not_modified() -> None:
    bars = good()
    before = list(bars)
    first = validate_opening_range(bars, OPEN)
    assert [validate_opening_range(bars, OPEN) for _ in range(3)] == [first] * 3
    assert bars == before


def test_or_v_51_no_look_ahead_the_result_for_a_prefix_is_not_closed_until_t_or_then_never_changes() -> None:
    day = [*good(), bar(20, h="999", low="1"), bar(25, h="999", low="1")]
    full = validate_opening_range(day, OPEN)
    for n in range(len(day) + 1):
        r: OrbRange = validate_opening_range(day[:n], OPEN)
        if n < 3:
            assert r.reasons == (R.OR_NOT_CLOSED,), n
        else:
            assert r == full, n  # once the range is closed, later bars cannot change it
