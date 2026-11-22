"""Framework diagnosis helpers (T-I144): bootstrap, common exit, controls, decomposition, trade check."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.diagnostics.decompose import (
    bucket_of,
    decompose,
    stop_of,
    stop_pct_of,
    verify_trade,
)
from app.backtest.diagnostics.sim import (
    TARGET_R,
    draw_control,
    eligible_signal_bars,
    exit_config,
    forward_returns,
    rules_from,
    session_times,
    simulate,
)
from app.backtest.diagnostics.stats import add, bootstrap_mean
from app.domain.types import Bar
from app.rulesets import load_ruleset

D = Decimal
OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST
RULES = rules_from(load_ruleset("pa-intraday", "0.4.0"))
SCHED = CostSchedule()


def day(prices: list[tuple[str, str, str, str]] | None = None) -> list[Bar]:
    """75 five-minute bars, 09:15..15:25 IST; flat at 100 unless `prices` overrides the leading bars."""
    rows = list(prices or [])
    rows += [("100", "100.2", "99.8", "100")] * (75 - len(rows))
    out = []
    for i, (o, h, lo, c) in enumerate(rows):
        s = OPEN + timedelta(minutes=5 * i)
        out.append(Bar(s, s + timedelta(minutes=5), D(o), D(h), D(lo), D(c)))
    return out


def test_session_times_are_ist_clock_times() -> None:
    or_end, cutoff, exit_time = session_times(day(), RULES)
    assert [t.astimezone(OPEN.tzinfo).strftime("%H:%M") for t in (or_end, cutoff, exit_time)] == [
        "04:00",
        "09:15",
        "09:45",
    ]  # 09:30, 14:45, 15:15 IST in UTC


def test_bootstrap_is_deterministic_and_brackets_the_mean() -> None:
    sums: dict = {}
    for d in range(40):
        add(sums, d, -0.2 + (0.1 if d % 2 else -0.1))
    one, two = bootstrap_mean(sums, resamples=500), bootstrap_mean(sums, resamples=500)
    assert one == two and one.n == 40
    assert abs(one.estimate - (-0.2)) < 1e-9 and one.low < one.estimate < one.high
    assert not one.excludes_zero() or one.high < 0  # centred well below zero
    assert one.material(0.05)


def test_bootstrap_difference_is_zero_for_identical_groups() -> None:
    sums: dict = {}
    for d in range(30):
        add(sums, d, (d % 5) / 10)
    diff = bootstrap_mean(sums, sums, resamples=300)
    assert diff.estimate == 0 and diff.low == 0 and diff.high == 0 and not diff.material(0.05)


def test_common_exit_stop_target_and_session_end() -> None:
    cfg = exit_config(RULES, session_times(day(), RULES)[2])
    entry, stop = D("100"), D("99")
    tgt = entry + TARGET_R * (entry - stop)
    stop_day = day([("100", "100.1", "98.5", "99.5")])
    t = simulate(stop_day, 0, "A", entry, stop, 10, tgt, cfg, SCHED)
    assert t.reason == "STOP" and t.exit == stop * D("0.9995")
    hit_day = day([("100", "103", "99.5", "102")])
    t = simulate(hit_day, 0, "A", entry, stop, 10, tgt, cfg, SCHED)
    assert t.reason == "TARGET" and t.exit == tgt
    flat = simulate(day(), 0, "A", entry, stop, 10, tgt, cfg, SCHED)
    assert flat.reason == "SESSION_END" and flat.exit_at.astimezone(UTC).hour == 9  # 15:15 IST


def test_optimistic_collision_takes_the_target() -> None:
    cfg = exit_config(RULES, session_times(day(), RULES)[2])
    entry, stop = D("100"), D("99")
    tgt = entry + TARGET_R * (entry - stop)
    both = day([("100", "103", "98.5", "100")])
    base = simulate(both, 0, "A", entry, stop, 10, tgt, cfg, SCHED)
    best = simulate(both, 0, "A", entry, stop, 10, tgt, cfg, SCHED, optimistic=True)
    assert base.reason == "STOP_COLLISION" and best.reason == "TARGET" and best.exit == tgt


def test_no_stop_slippage_and_fixed_horizon_variants() -> None:
    _, _, exit_time = session_times(day(), RULES)
    entry, stop = D("100"), D("99")
    tgt = entry + TARGET_R * (entry - stop)
    stop_day = day([("100", "100.1", "98.5", "99.5")])
    free = simulate(
        stop_day, 0, "A", entry, stop, 10, tgt, exit_config(RULES, exit_time, stop_slippage=False), SCHED
    )
    assert free.exit == stop
    drift = day(
        [
            ("100", "100.3", "99.9", "100.2"),
            ("100.2", "100.4", "100.1", "100.3"),
            ("100.3", "100.6", "100.2", "100.5"),
        ]
    )
    h = simulate(drift, 0, "A", entry, stop, 10, tgt, exit_config(RULES, exit_time), SCHED, horizon=3)
    assert h.reason == "HORIZON" and h.exit == D("100.5")


def test_forward_returns_use_the_close_h_bars_after_the_signal_bar() -> None:
    bars = day(
        [("100", "101", "99.9", "100.5"), ("100.5", "101", "100", "101"), ("101", "102", "100", "102")]
    )
    f = forward_returns(bars, 0, D("100"), D("99"), session_times(bars, RULES)[2])
    assert f["h3"] == (2.0, 2.0)  # close of the third bar from the fill bar: +2% = 2 stop distances
    assert "session" in f


def rng(seed: object = "1|A|d|0") -> random.Random:
    return random.Random(seed)  # noqa: S311


def test_controls_are_seeded_filled_by_the_real_rule_and_inside_the_window() -> None:
    bars = day()
    or_end, cutoff, _ = session_times(bars, RULES)
    pool = eligible_signal_bars(bars, or_end, cutoff)
    assert bars[pool[0]].end >= or_end and bars[pool[-1] + 1].start < cutoff
    a = draw_control(bars, "A", D("1.0"), rng(), RULES, SCHED)
    b = draw_control(bars, "A", D("1.0"), rng(), RULES, SCHED)
    assert a is not None and b is not None and a.trade == b.trade
    assert bars[a.fill_index].start >= or_end and bars[a.fill_index].start < cutoff
    # the stop distance is the requested percent of the signal-bar close; qty respects the risk unit
    assert abs(stop_pct_of(a.trade) - D("1.0")) < D("0.1")  # fill slippage moves it by about 0.05 points
    assert a.trade.risk_amount <= RULES.risk_unit


def test_controls_respect_the_one_position_rule() -> None:
    bars = day()
    rng = random.Random(1)  # noqa: S311
    c = draw_control(bars, "A", D("1.0"), rng, RULES, SCHED, after_index=len(bars) - 3)
    assert c is None or c.fill_index > len(bars) - 3


def test_decomposition_identity_and_buckets() -> None:
    _, _, exit_time = session_times(day(), RULES)
    entry_bar = day([("100", "100.4", "98.0", "99")])
    fill = D("100") * D("1.0005")
    stop = D("99")
    from app.backtest.trade import Position, close_trade

    pos = Position("A", "S", 0, "", 100, fill, stop, fill * 3, entry_bar[0].start, entry_bar[0].start)
    t = close_trade(pos, stop * D("0.9995"), entry_bar[0].start, "STOP", SCHED)
    d = decompose(t, entry_bar[0], D("99.9"), RULES.slippage_pct)
    assert abs(d.r_net - (d.before_friction - d.entry_slip - d.stop_slip - d.charges)) < 1e-9
    assert d.entry_slip > 0 and d.stop_slip > 0 and d.charges > 0
    assert stop_of(t) == stop
    assert [bucket_of(D(x)) for x in ("0.10", "0.15", "0.30", "0.99", "1.5", "2.0", "2.5")] == [
        -1,
        0,
        1,
        2,
        3,
        3,
        -1,
    ]
    _ = exit_time


def test_verify_trade_accepts_a_correct_trade_and_flags_a_wrong_one() -> None:
    from dataclasses import replace

    from app.backtest.trade import Position, close_trade

    bars = day([("100", "100.4", "98.0", "99")])
    _, _, exit_time = session_times(bars, RULES)
    fill = D("100") * D("1.0005")
    pos = Position("A", "S", 0, "", 100, fill, D("99"), fill * 3, bars[0].start, bars[0].start)
    t = close_trade(pos, D("99") * D("0.9995"), bars[0].start, "STOP", SCHED)
    assert verify_trade(bars, t, RULES.slippage_pct, exit_time) == []
    bad = replace(t, exit=D("98.9"))
    assert verify_trade(bars, bad, RULES.slippage_pct, exit_time)
