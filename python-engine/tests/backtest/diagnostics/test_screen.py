"""Fast screening protocol: minimal entries, filters, promotion and confirmation rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.diagnostics.screen import (
    EntryParams,
    confirmed,
    detect,
    detect_m1,
    detect_m2,
    detect_m3,
    entry_params,
    floor_tick,
    passes_stop,
    promoted,
    session_halves,
    tier1_variants,
    variant_id,
)
from app.backtest.diagnostics.sim import fill_and_run, rules_from
from app.backtest.diagnostics.stats import add, bootstrap_mean
from app.rulesets import load_ruleset

from .test_diagnostics import day

D = Decimal
PARAMS = entry_params(load_ruleset("pa-intraday", "0.4.0"))
OR3 = [("100", "101", "99.5", "100.5")] * 3  # OR_HIGH 101, OR_LOW 99.5, width 1.5%
RULES = rules_from(load_ruleset("pa-intraday", "0.4.0"))


def test_entry_parameters_come_from_the_ruleset() -> None:
    assert (PARAMS.bb, PARAMS.sb, PARAMS.reclaim_bars) == (D("0.05"), D("0.05"), 6)
    assert (PARAMS.or_min_pct, PARAMS.or_max_pct) == (D("0.3"), D("2.0"))
    assert (PARAMS.min_stop_pct, PARAMS.max_stop_pct) == (D("0.15"), D("2.0"))


def test_floor_tick_rounds_down() -> None:
    assert floor_tick(D("99.4497")) == D("99.40") and floor_tick(D("99.45")) == D("99.45")


def test_m1_signals_on_the_first_close_above_the_range_and_stops_below_its_low() -> None:
    bars = day([*OR3, ("100.5", "101.1", "100.4", "101.04"), ("101", "101.5", "100.9", "101.2")])
    sig = detect_m1(bars, PARAMS)
    assert sig is not None and (sig.entry, sig.index, sig.ref) == ("M1", 4, D("101.2"))  # 101.04 < 101.0505
    assert sig.stop == floor_tick(D("99.5") * D("0.9995")) == D("99.45")
    assert abs(sig.stop_pct - D("1.73")) < D("0.01")


def test_m1_range_width_gate_and_no_signal() -> None:
    narrow = [("100", "100.1", "99.95", "100")] * 3  # 0.15% wide
    assert detect_m1(day([*narrow, ("100", "101", "99.9", "100.9")]), PARAMS) is None
    wide = [("100", "104", "99", "100")] * 3  # 5%
    assert detect_m1(day([*wide, ("100", "106", "99.9", "105.9")]), PARAMS) is None
    assert detect_m1(day(OR3), PARAMS) is None  # never closes above


def test_signals_do_not_look_ahead() -> None:
    bars = day(
        [
            *OR3,
            ("100.5", "100.9", "100.4", "100.8"),
            ("100.8", "101.6", "100.7", "101.5"),
            ("101.5", "103", "101", "102"),
        ]
    )
    full = detect_m1(bars, PARAMS)
    assert full is not None and full.index == 4
    assert detect_m1(bars[:4], PARAMS) is None  # before the signal bar closes there is no signal
    assert detect_m1(bars[:5], PARAMS) == full  # later bars never change it


def test_m2_needs_an_open_below_the_previous_day_high_and_uses_the_session_low() -> None:
    bars = day([("100", "100.6", "99.2", "100.4"), ("100.4", "100.9", "100", "100.6"), ("100.6", "101", "100.2", "100.8"),
                ("100.8", "101.2", "100.6", "101.0"), ("101.0", "102", "100.9", "101.9")])  # fmt: skip
    sig = detect_m2(bars, PARAMS, D("101.5"))
    assert sig is not None and (sig.index, sig.ref) == (4, D("101.9"))
    assert sig.stop == floor_tick(D("99.2") * D("0.9995"))  # the session low so far
    assert detect_m2(bars, PARAMS, D("100")) is None  # the session opened at or above the level
    assert detect_m2(bars, PARAMS, None) is None


def test_m3_breakdown_then_reclaim_within_the_window() -> None:
    bd = ("99.6", "99.7", "98.8", "99.0")  # closes below 99.5 * 0.9995
    bars = day([*OR3, bd, ("99.0", "99.3", "98.5", "99.2"), ("99.2", "99.9", "99.1", "99.6")])
    sig = detect_m3(bars, PARAMS)
    assert sig is not None and (sig.index, sig.ref) == (5, D("99.6"))
    assert sig.stop == floor_tick(D("98.5") * D("0.9995"))  # lowest low from the breakdown to the reclaim
    late = day([*OR3, bd, *[("99.0", "99.3", "98.9", "99.1")] * 6, ("99.1", "99.9", "99.0", "99.7")])
    assert detect_m3(late, PARAMS) is None  # the seventh bar is outside the 6-bar window
    ok = day([*OR3, bd, *[("99.0", "99.3", "98.9", "99.1")] * 5, ("99.1", "99.9", "99.0", "99.7")])
    assert detect_m3(ok, PARAMS) is not None  # the sixth bar is inside it


def test_m3_only_the_first_breakdown_counts() -> None:
    bd = ("99.6", "99.7", "98.8", "99.0")
    bars = day([*OR3, bd, *[("99.0", "99.3", "98.9", "99.1")] * 6, bd, ("99.0", "99.9", "99.0", "99.7")])
    assert detect_m3(bars, PARAMS) is None


def test_detect_dispatch_and_unknown_entry() -> None:
    bars = day([*OR3, ("100.5", "101.6", "100.4", "101.5")])
    assert detect("M1", bars, PARAMS) == detect_m1(bars, PARAMS)
    try:
        detect("M9", bars, PARAMS)
    except ValueError as e:
        assert "unknown entry" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_stop_filters_and_variant_family() -> None:
    p: EntryParams = PARAMS
    assert passes_stop(D("0.2"), D(0), p) and not passes_stop(D("0.1"), D(0), p)
    assert not passes_stop(D("2.5"), D(0), p) and passes_stop(D("2.0"), D(0), p)
    assert passes_stop(D("0.75"), D("0.75"), p) and not passes_stop(D("0.74"), D("0.75"), p)
    assert passes_stop(D("1.5"), D("1.0"), p) and not passes_stop(D("0.9"), D("1.0"), p)
    ids = [v[0] for v in tier1_variants()]
    assert len(ids) == 9 and len(set(ids)) == 9
    assert variant_id("M1", D(0)) == "M1@none" and variant_id("M3", D("0.75")) == "M3@>=0.75%"


def test_promotion_and_confirmation_rules() -> None:
    assert promoted(100, 0.02, 0.05, 0.001)
    assert not promoted(99, 0.02, 0.06, 0.01)  # too few trades
    assert not promoted(500, -0.01, 0.06, 0.01)  # gross not above zero
    assert not promoted(500, 0.02, 0.049, 0.01)  # edge below 0.05R
    assert not promoted(500, 0.02, 0.06, 0.0)  # interval touches zero
    assert confirmed(100, 0.05, 0.001, [0.02, 0.08])
    assert not confirmed(100, 0.05, 0.001, [0.02, -0.01])  # sign flips in one half
    assert not confirmed(100, 0.05, 0.0, [0.02, 0.08])
    assert not confirmed(99, 0.05, 0.001, [0.02, 0.08])


def test_session_halves_split_dates_in_order() -> None:
    days = [date(2025, 1, d) for d in (6, 2, 3, 7, 8)]
    first, second = session_halves(days)
    assert first == {date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)}
    assert second == {date(2025, 1, 7), date(2025, 1, 8)}


def test_the_99_percent_interval_is_wider_than_the_95() -> None:
    sums: dict = {}
    for d in range(60):
        add(sums, d, ((d * 7) % 11 - 5) / 10)
    a = bootstrap_mean(sums, resamples=800)
    b = bootstrap_mean(sums, resamples=800, level=0.99)
    assert b.low <= a.low and b.high >= a.high and a.estimate == b.estimate


def test_fill_and_run_uses_the_real_fill_rule() -> None:
    bars = day([*OR3, ("100.5", "101.6", "100.4", "101.5"), ("101.5", "103.9", "101.4", "103.5")])
    c = fill_and_run(bars, 3, "A", D("101.5"), D("99.45"), RULES, CostSchedule())
    assert c is not None and c.fill_index == 4 and c.trade.entry == D("101.5") * D("1.0005")
    assert (
        fill_and_run(bars, 3, "A", D("101.5"), D("101.6"), RULES, CostSchedule()) is None
    )  # stop above entry
    assert (
        fill_and_run(bars, len(bars) - 1, "A", D("100"), D("99"), RULES, CostSchedule()) is None
    )  # no next bar
    gap = day([*OR3, ("100.5", "101.6", "100.4", "101.5"), ("103", "104", "102.9", "103.5")])
    assert fill_and_run(gap, 3, "A", D("101.5"), D("99.45"), RULES, CostSchedule()) is None  # gap above 0.3%
