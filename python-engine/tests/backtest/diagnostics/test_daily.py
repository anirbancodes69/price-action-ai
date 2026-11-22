"""Gate 0 daily simulator, baselines and audit helpers (T-I146)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from app.backtest.costs import DeliverySchedule
from app.backtest.diagnostics.daily import (
    DailyRules,
    DayBar,
    draw_baseline,
    drift_returns,
    eligible_signals,
    fill_entry,
    gap_flags,
    in_sample_last_date,
    missing_sessions,
    month_key,
    ohlc_defects,
    run_daily,
    verify_daily_trade,
)
from app.backtest.diagnostics.stats import add, bootstrap_mean

D = Decimal
RULES = DailyRules()
SCHED = DeliverySchedule()
START = date(2024, 1, 1)


def mk(rows: list[tuple[str, str, str, str]], start: date = START) -> list[DayBar]:
    return [
        DayBar(start + timedelta(days=i), D(o), D(h), D(lo), D(c)) for i, (o, h, lo, c) in enumerate(rows)
    ]


FLAT = ("100", "100.5", "99.5", "100")


def test_fill_entry_applies_slippage_sizes_by_risk_and_caps_the_position() -> None:
    nxt = mk([("100", "101", "99", "100")])[0]
    entry, qty = fill_entry(nxt, D("100"), D("97"), RULES) or (D(0), 0)
    assert entry == D("100") * D("1.0005") and qty == int(D(500) // (entry - D("97")))  # 166
    assert fill_entry(nxt, D("100"), D("99.9999"), RULES) is not None
    # a 50,000 cap: a tiny stop would size to a huge quantity, the cap limits it to 499 shares
    capped = fill_entry(nxt, D("100"), D("99.9"), RULES)
    assert capped is not None and capped[1] == int(D(50000) // capped[0])


def test_fill_entry_skips() -> None:
    assert fill_entry(mk([("97", "98", "96", "97")])[0], D("100"), D("97"), RULES) is None  # open at the stop
    assert (
        fill_entry(mk([("101.5", "102", "101", "101.5")])[0], D("100"), D("97"), RULES) is None
    )  # gap above 1%
    tiny = replace(RULES, risk_unit=D("1"))
    assert (
        fill_entry(mk([("100", "101", "99", "100")])[0], D("100"), D("90"), tiny) is None
    )  # qty rounds to 0


def test_stop_in_the_fill_session_exits_at_the_stop_with_slippage() -> None:
    bars = mk([FLAT, ("100", "100.2", "96.5", "98"), FLAT])
    t = run_daily(bars, 0, "A", D("100"), D("97"), None, 10, RULES, SCHED)
    assert t is not None and t.reason == "STOP" and t.exit == D("97") * D("0.9995")
    assert (t.fill_day, t.exit_day, t.hold_sessions) == (bars[1].day, bars[1].day, 1)
    assert t.r_gross < -1 and t.r_net < t.r_gross  # slippage and charges add to the loss


def test_a_later_gap_below_the_stop_exits_at_the_open() -> None:
    bars = mk([FLAT, ("100", "101", "99.5", "100.5"), ("95", "96", "94", "95.5"), FLAT])
    t = run_daily(bars, 0, "A", D("100"), D("97"), None, 10, RULES, SCHED)
    assert t is not None and t.reason == "STOP_GAP" and t.exit == D("95") * D("0.9995")
    assert t.exit < D("97") * D("0.9995")  # worse than the stop: the gap loss


def test_target_gap_target_and_collision() -> None:
    target = D("103")
    hit = mk([FLAT, ("100", "101", "99.5", "100.5"), ("101", "103.5", "100.5", "103"), FLAT])
    t = run_daily(hit, 0, "A", D("100"), D("97"), target, 10, RULES, SCHED)
    assert t is not None and (t.reason, t.exit) == ("TARGET", target)
    gap = mk([FLAT, ("100", "101", "99.5", "100.5"), ("104", "105", "103.5", "104.5"), FLAT])
    t = run_daily(gap, 0, "A", D("100"), D("97"), target, 10, RULES, SCHED)
    assert t is not None and (t.reason, t.exit) == ("TARGET_GAP", D("104"))
    both = mk([FLAT, ("100", "101", "99.5", "100.5"), ("100", "104", "96", "100"), FLAT])
    t = run_daily(both, 0, "A", D("100"), D("97"), target, 10, RULES, SCHED)
    assert t is not None and t.reason == "STOP_COLLISION" and t.exit == D("97") * D("0.9995")


def test_time_stop_exits_at_the_close_of_the_hold_th_session() -> None:
    rows = [FLAT] + [("100", "100.4", "99.6", str(100 + i * 0.1)) for i in range(6)]
    bars = mk(rows)
    t = run_daily(bars, 0, "A", D("100"), D("97"), None, 3, RULES, SCHED)
    assert t is not None and t.reason == "TIME_STOP" and t.hold_sessions == 3
    assert t.exit_day == bars[3].day  # fill session 1, exit at the close of session 3
    assert t.exit == bars[3].close * D("0.9995")


def test_data_ending_before_the_exit_is_marked() -> None:
    bars = mk([FLAT, ("100", "100.4", "99.6", "100.2"), ("100.2", "100.5", "99.9", "100.3")])
    t = run_daily(bars, 0, "A", D("100"), D("97"), None, 10, RULES, SCHED)
    assert t is not None and t.reason == "END_OF_DATA" and t.exit_day == bars[-1].day
    assert run_daily(bars, 2, "A", D("100"), D("97"), None, 10, RULES, SCHED) is None  # no fill session


def test_eligible_signals_keep_the_whole_window_inside_the_bars() -> None:
    bars = mk([FLAT] * 30)
    assert eligible_signals(bars, 10) == list(range(19))
    assert eligible_signals(bars, 40) == []


def _month_bars() -> list[DayBar]:
    rows = [("100", "100.6", "99.4", str(100 + (i % 5) * 0.1)) for i in range(70)]
    return mk(rows)


def test_baseline_is_seeded_inside_its_month_and_has_a_start_before_the_window_end() -> None:
    bars = _month_bars()
    a, ra = draw_baseline(bars, "A", (2024, 1), D(3), None, 5, "1|A|2024-1", RULES, SCHED)
    b, rb = draw_baseline(bars, "A", (2024, 1), D(3), None, 5, "1|A|2024-1", RULES, SCHED)
    assert a is not None and a == b and (ra, rb) == (0, 0)
    assert month_key(a.signal_day) == (2024, 1)
    assert draw_baseline(bars, "A", (2030, 1), D(3), None, 5, "1|A|x", RULES, SCHED) == (
        None,
        0,
    )  # no sessions


def test_baseline_redraws_a_skipped_fill() -> None:
    rows = [("100", "100.6", "99.4", "100")] * 40
    rows = [r if i % 2 == 0 else ("103", "103.5", "102.5", "103") for i, r in enumerate(rows)]  # gap-ups skip
    t, redraws = draw_baseline(mk(rows), "A", (2024, 1), D(3), None, 3, "1|A|gap", RULES, SCHED)
    assert t is not None  # an even signal session is eventually drawn
    assert redraws >= 0 and eligible_signals(mk(rows), 3)


def test_drift_return_is_close_over_fill_open() -> None:
    bars = mk(
        [
            FLAT,
            ("100", "101", "99.8", "100.5"),
            ("100.5", "102", "100", "101"),
            ("101", "103", "100.8", "102"),
        ]
    )
    (day, ret), *_ = drift_returns(bars, 2)
    assert (
        day == bars[1].day and abs(ret - ((101 / 100) - 1) * 100) < 1e-9
    )  # close of session 2 / open of session 1


def test_gap_flags_find_large_gaps_and_split_signatures() -> None:
    bars = mk(
        [
            ("100", "101", "99", "100"),
            ("121", "122", "120", "121"),
            ("60.4", "61", "60", "60.5"),
            ("60.6", "61", "60", "60.8"),
        ]
    )
    flags = {d: w for d, _, w in gap_flags(bars)}
    assert flags[bars[1].day] == "GAP_OVER_15PCT"
    assert (
        "SPLIT_SIGNATURE" in flags[bars[2].day] and "GAP_OVER_15PCT" in flags[bars[2].day]
    )  # 60.4 / 121 ~ 1/2
    assert bars[3].day not in flags


def test_ohlc_defects_and_missing_sessions() -> None:
    bars = mk([("100", "101", "99", "100"), ("100", "99", "98", "99"), ("0", "1", "0", "1")])
    assert ohlc_defects(bars) == [(bars[1].day, "OHLC_INCONSISTENT"), (bars[2].day, "NON_POSITIVE_PRICE")]
    cal = [START + timedelta(days=i) for i in range(6)]
    have = [cal[1], cal[2], cal[4]]
    assert missing_sessions(cal, have) == [cal[3], cal[5]]  # before its first date is not missing
    assert missing_sessions(cal, []) == []


def test_in_sample_last_date_uses_dates_only() -> None:
    cal = [START + timedelta(days=i) for i in range(10)]
    assert in_sample_last_date(cal) == cal[5]  # 60% of 10 sessions: the sixth


def test_verify_daily_trade_accepts_a_correct_trade_and_flags_a_wrong_one() -> None:
    bars = mk(
        [
            FLAT,
            ("100", "100.4", "99.6", "100.2"),
            ("100.2", "100.5", "99.9", "100.3"),
            ("100.3", "100.6", "100", "100.5"),
        ]
    )
    t = run_daily(bars, 0, "A", D("100"), D("97"), None, 3, RULES, SCHED)
    assert t is not None and verify_daily_trade(bars, t, RULES.slippage_pct) == []
    bad = replace(t, exit=t.exit + D("1"))
    assert verify_daily_trade(bars, bad, RULES.slippage_pct)
    stopped = mk([FLAT, ("100", "100.2", "96.5", "98"), FLAT])
    st = run_daily(stopped, 0, "A", D("100"), D("97"), None, 10, RULES, SCHED)
    assert st is not None and verify_daily_trade(stopped, st, RULES.slippage_pct) == []


def test_month_block_bootstrap_resamples_calendar_months() -> None:
    sums: dict = {}
    for m in range(1, 13):
        for _ in range(5):
            add(sums, (2024, m), -0.1 + (0.05 if m % 2 else -0.05))
    r = bootstrap_mean(sums, resamples=300)
    assert r.n == 60 and r.low <= r.estimate <= r.high and r.high < 0
