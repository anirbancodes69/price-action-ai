"""E6: the matched random-entry control (synthetic bars; nothing here is an experiment result)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app.backtest.b0_eligibility import B0Reference, Eligibility, PriceBasis, TickStatus
from app.backtest.controls import (
    MAX_TIME_REDRAWS,
    OrbSignal,
    balance_report,
    control_candidates,
    control_signals,
    draw_control_set,
    gate_reason,
    simulate_control_set,
)
from app.backtest.costs import CostSchedule
from app.backtest.reference_tables import EventTable, SessionFactsTable
from app.backtest.replay import SessionSpec, SymbolData
from app.backtest.run import SessionInput
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import run_strategy_backtest
from app.domain.ticks import TickTable
from app.rulesets import load_ruleset

from ..trading._session import CLOSE, OPEN, mk
from .b0_support import INDEPENDENT_RD, ctx

D = Decimal
P = load_ruleset("pa-intraday", "0.6.0")
P = replace(P, values={**P.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5})
SLIP = SlippageModel.uniform(D("0.05"), "u")
OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
CQ = ("1002", "1004", "1001", "1003")  # opens 0.05% under the previous close: a fill passes RC-04
FLAT = ("1003", "1004", "1001", "1003")  # opens at the previous close: RC-04 rejects (finding F-1)
BREAK = ("1003", "1007", "1002", "1006")
ELIG = Eligibility(
    True, None, (), TickStatus.TICK_VERIFIED_PASS, D("0.05"), PriceBasis.TRADED_SCALE_VERIFIED, ()
)
DAYS = [date(2025, 3, 3) + timedelta(days=i) for i in range(10)]


def _session(day: date, rows: list[tuple[str, str, str, str]], names: list[str]) -> SessionInput:
    off = timedelta(days=(day - OPEN.date()).days)
    bars = mk(rows, start=OPEN + off)
    spec = SessionSpec(day, OPEN + off, CLOSE + off)
    return SessionInput(spec, [SymbolData(n, bars, bars, None, D("0.05")) for n in names])


def _world(
    rows: list[tuple[str, str, str, str]], names: list[str] | None = None, days: list[date] | None = None
):  # type: ignore[no-untyped-def]
    names = names or ["AAA"]
    sessions = [_session(d, rows, names) for d in (days or DAYS)]
    elig = {(n, d): ELIG for n in names for d in (days or DAYS)}
    return sessions, elig


GOOD = OR3 + [CQ] * 12
T = [time(9, 40), time(9, 50), time(10, 5)]


def _orb(n: int = 3, symbol: str = "AAA") -> list[OrbSignal]:
    return [OrbSignal(symbol, DAYS[i], T[i % 3]) for i in range(n)]


def test_candidates_are_the_eligible_sessions_inside_the_width_band_whether_or_not_a_breakout_happened() -> (
    None
):
    sessions, elig = _world(GOOD)
    assert len(control_candidates(sessions, elig, P)) == len(DAYS)
    elig[("AAA", DAYS[0])] = replace(ELIG, eligible=False, reason="TICK_UNKNOWN")
    assert len(control_candidates(sessions, elig, P)) == len(DAYS) - 1
    wide = [("1000", "1030", "1000", "1000.5")] * 3 + [CQ] * 6
    s2, e2 = _world(wide)
    assert control_candidates(s2, e2, P) == []  # SC-03: too wide
    narrow = [("1000", "1002", "1000", "1000.5")] * 3 + [CQ] * 6
    s3, e3 = _world(narrow)
    assert control_candidates(s3, e3, P) == []


def test_the_draw_is_deterministic_matches_frequency_and_time_and_never_reuses_a_session() -> None:
    sessions, elig = _world(GOOD)
    cands = control_candidates(sessions, elig, P)
    a = draw_control_set(7, _orb(), cands, P, D("100000"), D("0.05"))
    b = draw_control_set(7, _orb(), cands, P, D("100000"), D("0.05"))
    assert a == b and len(a.entries) == 3 and a.unplaced == 0
    assert len({(e.symbol, e.day) for e in a.entries}) == 3  # at most one entry per instrument-session
    sig = control_signals(a, cands)
    assert all(s.signal_time in set(T) for s in sig)  # times come from the ORB distribution
    assert all(e.day.month == 3 for e in a.entries)
    other = {draw_control_set(s, _orb(), cands, P, D("100000"), D("0.05")).entries for s in range(1, 8)}
    assert len(other) > 1  # the seed matters


def test_counts_per_instrument_and_month_equal_the_orb_counts() -> None:
    sessions, elig = _world(GOOD, ["AAA", "BBB"])
    cands = control_candidates(sessions, elig, P)
    orb = _orb(3, "AAA") + _orb(2, "BBB")
    cs = draw_control_set(1, orb, cands, P, D("100000"), D("0.05"))
    got = sorted(e.symbol for e in cs.entries)
    assert got == ["AAA"] * 3 + ["BBB"] * 2
    rep = balance_report(orb, control_signals(cs, cands), [D(1)], [D(1)])
    assert rep.counts_identical


def test_a_draw_that_fails_a_gate_is_redrawn_and_the_redraw_rate_is_reported() -> None:
    sessions, elig = _world(OR3 + [CQ] * 3 + [FLAT] * 12)  # only bars before 09:45 fill; later opens do not
    cands = control_candidates(sessions, elig, P)
    cs = draw_control_set(3, [OrbSignal("AAA", DAYS[0], time(10, 5))] * 3, cands, P, D("100000"), D("0.05"))
    assert cs.draws >= len(cs.entries) and cs.redraws == cs.draws - len(cs.entries)
    assert cs.gate_counts and set(cs.gate_counts) <= {"SKIPPED_RR_DEGRADED", "NO_BAR_AT_TIME"}


def test_finding_f1_also_strains_the_control_because_it_uses_the_same_fill_rule() -> None:
    sessions, elig = _world(OR3 + [FLAT] * 12)
    cands = control_candidates(sessions, elig, P)
    cs = draw_control_set(1, _orb(), cands, P, D("100000"), D("0.05"))
    assert cs.entries == () and cs.unplaced == 3 and cs.strained
    assert cs.redraws == cs.draws and cs.gate_counts == {"SKIPPED_RR_DEGRADED": cs.draws}
    assert cs.session_redraws >= 1 and cs.draws % MAX_TIME_REDRAWS == 0


def test_the_gate_uses_the_replays_functions_cutoff_and_stop_distance() -> None:
    sessions, elig = _world(GOOD)
    c = control_candidates(sessions, elig, P)[0]
    last = len(c.sym.bars_5m) - 2
    assert gate_reason(c, 3, P, D("100000"), D("0.05")) is None
    cutoff_rows = OR3 + [CQ] * 70  # a signal bar ending after 14:45
    s2, e2 = _world(cutoff_rows)
    c2 = control_candidates(s2, e2, P)[0]
    late = max(i for i in range(3, len(c2.sym.bars_5m) - 1))
    assert gate_reason(c2, late, P, D("100000"), D("0.05")) == "AFTER_ENTRY_CUTOFF"
    assert last > 3


def test_no_look_ahead_the_draw_does_not_depend_on_bars_after_the_next_open() -> None:
    sessions, elig = _world(GOOD)
    cands = control_candidates(sessions, elig, P)
    cs = draw_control_set(5, _orb(), cands, P, D("100000"), D("0.05"))
    changed = []
    for s in sessions:
        hit = [e for e in cs.entries if e.day == s.spec.session_date]
        sym = s.symbols[0]
        bars = list(sym.bars_5m)
        if hit:
            for i in range(hit[0].bar_index + 2, len(bars)):
                b = bars[i]
                bars[i] = replace(b, high=b.high + 500, low=b.low - 400, close=b.close - 300)
        changed.append(SessionInput(s.spec, [replace(sym, bars_5m=bars, bars_15m=bars)]))
    cands2 = control_candidates(changed, elig, P)
    cs2 = draw_control_set(5, _orb(), cands2, P, D("100000"), D("0.05"))
    assert [(e.symbol, e.day, e.bar_index) for e in cs2.entries] == [
        (e.symbol, e.day, e.bar_index) for e in cs.entries
    ]


@pytest.mark.usefixtures("small_b0_hash")
def test_a_control_is_replayed_by_the_same_code_as_an_orb_trade() -> None:
    """Force the control at the bar where B0 signals: every trade field must equal the ORB trade."""
    rows = [*OR3, CQ, BREAK, ("1005", "1020", "1004", "1019"), ("1019", "1020", "1018", "1019")]
    sessions, elig = _world(rows, days=[DAYS[0]])
    orb = run_strategy_backtest(
        "orb_b0",
        "4a",
        sessions,
        P,
        D("100000"),
        CostSchedule(),
        "e",
        "d",
        "u",
        slippage=SLIP,
        reference_data=INDEPENDENT_RD,
        b0_context=ctx(P),
    )
    assert len(orb.trades) == 1
    cands = control_candidates(sessions, elig, P)
    from app.backtest.controls import ControlEntry, ControlSet

    cs = ControlSet(1, (ControlEntry("AAA", DAYS[0], 4),), 1, 0, 0, 0)
    ref = B0Reference(
        TickTable([]), EventTable([]), SessionFactsTable([], []), {}, INDEPENDENT_RD, None, ctx(P)
    )
    ctl = simulate_control_set(cs, sessions, P, "4a", D("100000"), "e", "d", "u", SLIP, ref)
    assert len(ctl.trades) == 1 and cands
    a, b = orb.trades[0], ctl.trades[0]
    # Labels only differ: the 15m context is a display label that B0 never reads; every price, size and cost is equal.
    blank = {"anchor": "", "setup_type": "", "context_15m": ""}
    assert replace(a, **blank) == replace(b, **blank)


def test_balance_checks_flag_count_time_and_stop_distance_differences() -> None:
    orb = [OrbSignal("AAA", DAYS[i], time(9, 40 + 5 * i)) for i in range(4)]
    same = list(orb)
    ok = balance_report(orb, same, [D(1)] * 4, [D(1)] * 4)
    assert ok.counts_identical and ok.max_cdf_gap_pooled == 0 and ok.flags == ()
    skew = [OrbSignal("AAA", DAYS[i], time(14, 0)) for i in range(4)]
    bad = balance_report(orb, skew, [D(1)] * 4, [D("1.5")] * 4)
    assert "CDF_GAP_POOLED_OVER_0.01" in bad.flags and "STOP_DISTANCE_MEDIAN_DIFFERS_OVER_25PCT" in bad.flags
    fewer = balance_report(orb, same[:3], [D(1)], [D(1)])
    assert not fewer.counts_identical and "COUNTS_NOT_IDENTICAL" in fewer.flags


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_empty_orb_input_gives_an_empty_control(seed: int) -> None:
    sessions, elig = _world(GOOD)
    cs = draw_control_set(seed, [], control_candidates(sessions, elig, P), P, D("100000"), D("0.05"))
    assert cs.entries == () and cs.draws == 0
