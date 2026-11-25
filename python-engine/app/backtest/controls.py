"""Matched random-entry control (MTC) for B0, validation plan §4.2 (E6). **Not executed in this task.**

This is not `diagnostics.sim.draw_control` (the M1-screen control). Design, from plan §4.2:
- Candidates are the instrument-sessions that B0 itself evaluated and found eligible (the same `Eligibility`
  objects, hence `MG-01`/`MG-02`) **and** whose range passes the width band (`SC-03`), whether or not a
  breakout happened.
- Per instrument and calendar month the control has as many entries as the ORB run has filled trades, at most
  one per instrument-session.
- The signal time of each entry is drawn from the empirical distribution of the ORB signal times (5m bins).
- A draw that fails a gate (cutoff, no target, `RC-01`, `RC-02`, or the `RC-04` fill checks, evaluated with
  the same functions the replay uses) is redrawn in time up to `MAX_TIME_REDRAWS` times, then in session. The
  redraw rate is reported; above `STRAIN_LIMIT` the control is flagged `CONTROL_STRAINED`.
- Sampling is deterministic: `random.Random(seed)` over sorted inputs; replicate seeds are 1 to K.
- No look-ahead: a control uses only the range (known at `t_OR`), the signal bar's close, and, for the fill
  precheck, the next open, exactly as an ORB trade does.
- The control trades are replayed through `run_backtest` with the same configuration, fill rule, exits, costs
  and slippage as the ORB run; the replay's analysis step is replaced by a forced signal at the drawn bar and
  nothing else (`forced_analyse`). Levels come from `b0_levels`, the function the B0 detector uses.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, time
from decimal import Decimal

from app.backtest.b0_eligibility import B0Reference, Eligibility
from app.backtest.costs import CostSchedule
from app.backtest.replay import AnalyseFn, SessionSpec, SymbolData
from app.backtest.run import BacktestResult, SessionInput, run_backtest
from app.backtest.strategy_run import strategy_config
from app.domain.analyse import AnalysisResult
from app.domain.levels import b0_levels
from app.domain.params import RulesetParams
from app.domain.risk.fill import simulate_entry
from app.domain.risk.validation import validate_stop
from app.domain.session import entry_cutoff
from app.domain.setups.orb_b0 import OrbB0Setup
from app.domain.setups.orb_range import validate_opening_range
from app.domain.setups.signal import ScoredSetup, Signal, SignalResult
from app.domain.setups.types import SetupDirection, SetupStatus, SetupType
from app.domain.snapshot import SnapshotCheck, SnapshotStatus
from app.ingestion.session import IST

MAX_TIME_REDRAWS = 20
STRAIN_LIMIT = Decimal("0.20")


@dataclass(frozen=True, slots=True)
class OrbSignal:
    """What the control needs of one filled ORB trade."""

    symbol: str
    day: date
    signal_time: time  # end of the signal bar, IST


@dataclass(frozen=True, slots=True)
class ControlCandidate:
    sym: SymbolData
    spec: SessionSpec
    day: date
    range_high: Decimal
    range_low: Decimal
    first: int  # index in `sym.bars_5m` of the session's first bar
    end_index: dict[time, int]  # signal-bar end time (IST) -> bar index, for bars with a next bar


@dataclass(frozen=True, slots=True)
class ControlEntry:
    symbol: str
    day: date
    bar_index: int  # index of the signal bar in the symbol's bars


@dataclass(frozen=True, slots=True)
class ControlSet:
    seed: int
    entries: tuple[ControlEntry, ...]
    draws: int
    redraws: int  # draws that failed a gate
    session_redraws: int
    unplaced: int  # entries that found no valid draw in any remaining session
    gate_counts: dict[str, int] = field(default_factory=dict)

    @property
    def redraw_rate(self) -> Decimal:
        return Decimal(self.redraws) / Decimal(self.draws) if self.draws else Decimal(0)

    @property
    def strained(self) -> bool:
        return self.redraw_rate > STRAIN_LIMIT or self.unplaced > 0


def control_candidates(
    sessions: Sequence[SessionInput],
    eligibility: Mapping[tuple[str, date], Eligibility],
    params: RulesetParams,
) -> list[ControlCandidate]:
    """Eligible instrument-sessions with a range inside the width band (`SC-03`). Same eligibility as ORB."""
    minutes = params.int_("session.opening_range_minutes")
    lo_pct, hi_pct = (
        params.decimal("setup.opening_range_min_pct"),
        params.decimal("setup.opening_range_max_pct"),
    )
    out: list[ControlCandidate] = []
    for s in sorted(sessions, key=lambda x: x.spec.session_date):
        for sym in sorted(s.symbols, key=lambda x: x.symbol):
            e = eligibility.get((sym.symbol, s.spec.session_date))
            if e is None or not e.eligible:
                continue
            bars = sym.bars_5m
            first = next((i for i, b in enumerate(bars) if b.start >= s.spec.session_open), None)
            if first is None:
                continue
            rng = validate_opening_range(bars[first:], s.spec.session_open, minutes)
            if not rng.valid or rng.or_high is None or rng.or_low is None:
                continue
            width = (rng.or_high - rng.or_low) / rng.or_low * 100
            if not lo_pct <= width <= hi_pct:
                continue
            ends = {
                bars[i].end.astimezone(IST).time(): i
                for i in range(first, len(bars) - 1)
                if bars[i].end >= rng.t_or
            }
            out.append(
                ControlCandidate(sym, s.spec, s.spec.session_date, rng.or_high, rng.or_low, first, ends)
            )
    return out


def gate_reason(
    c: ControlCandidate, index: int, params: RulesetParams, capital: Decimal, entry_slippage_pct: Decimal
) -> str | None:
    """The control's gates, with the functions the replay uses; `None` means the draw is usable."""
    bars = c.sym.bars_5m
    bar, nxt = bars[index], bars[index + 1]
    cutoff = entry_cutoff(c.spec.session_close, params.int_("session.entry_cutoff_minutes_before_close"))
    if bar.end > cutoff:
        return "AFTER_ENTRY_CUTOFF"
    lv = b0_levels(bar.close, c.range_low, params, c.sym.tick)
    if lv.target is None:
        return "NO_TARGET"
    if lv.rr_below_min:
        return "RR_BELOW_MINIMUM"
    errs = validate_stop(
        lv.entry,
        lv.stop,
        c.sym.tick,
        params.decimal("risk.min_stop_distance_pct"),
        params.decimal("risk.max_stop_distance_pct"),
    )
    if errs:
        return errs[0]
    budget = capital * params.decimal("risk.default_risk_per_trade_pct") / 100
    fill = simulate_entry(
        nxt.open,
        lv.entry,
        lv.stop,
        lv.target,
        10**9,
        budget,
        Decimal(10) ** 12,
        params.decimal("risk.min_rr"),
        params.decimal("risk.max_entry_gap_pct"),
        nxt.start,
        cutoff,
        entry_slippage_pct,
    )
    return fill.reason if not fill.filled else None


def draw_control_set(
    seed: int,
    orb: Sequence[OrbSignal],
    candidates: Sequence[ControlCandidate],
    params: RulesetParams,
    capital: Decimal,
    entry_slippage_pct: Decimal,
) -> ControlSet:
    """One control set. Deterministic in `(seed, inputs)`; iteration is over sorted keys, never set order."""
    rng = random.Random(seed)  # noqa: S311 (reproducible simulation sampling, not security)
    times = sorted(o.signal_time for o in orb)
    if not times:
        return ControlSet(seed, (), 0, 0, 0, 0)
    by_group: dict[tuple[str, int, int], list[ControlCandidate]] = defaultdict(list)
    for c in sorted(candidates, key=lambda x: (x.sym.symbol, x.day)):
        by_group[(c.sym.symbol, c.day.year, c.day.month)].append(c)
    need: dict[tuple[str, int, int], int] = defaultdict(int)
    for o in orb:
        need[(o.symbol, o.day.year, o.day.month)] += 1
    entries: list[ControlEntry] = []
    draws = redraws = session_redraws = unplaced = 0
    gates: dict[str, int] = defaultdict(int)
    for key in sorted(need):
        pool = list(by_group.get(key, []))
        for _ in range(need[key]):
            placed = False
            while pool and not placed:
                c = pool.pop(rng.randrange(len(pool)))
                for _attempt in range(MAX_TIME_REDRAWS):
                    t = times[rng.randrange(len(times))]
                    idx = c.end_index.get(t)
                    draws += 1
                    reason = (
                        "NO_BAR_AT_TIME"
                        if idx is None
                        else gate_reason(c, idx, params, capital, entry_slippage_pct)
                    )
                    if reason is None:
                        assert idx is not None
                        entries.append(ControlEntry(c.sym.symbol, c.day, idx))
                        placed = True
                        break
                    redraws += 1
                    gates[reason] += 1
                if not placed:
                    session_redraws += 1
            if not placed:
                unplaced += 1
    return ControlSet(
        seed, tuple(entries), draws, redraws, session_redraws, unplaced, dict(sorted(gates.items()))
    )


def forced_analyse(forced: Mapping[tuple[str, date], int]) -> AnalyseFn:
    """The replay's analysis step for controls: a confirmed signal at the drawn bar, nothing elsewhere."""

    def run(sym: SymbolData, k: int, spec: SessionSpec, params: RulesetParams) -> AnalysisResult:
        check = SnapshotCheck(SnapshotStatus.VALID, ())
        base = AnalysisResult(params.code, params.version, check, "", "", None, None, None, None)
        idx = forced.get((sym.symbol, spec.session_date))
        if idx is None or k != idx + 1:
            return base
        first = next(i for i, b in enumerate(sym.bars_5m) if b.start >= spec.session_open)
        rng = validate_opening_range(
            sym.bars_5m[first : idx + 1], spec.session_open, params.int_("session.opening_range_minutes")
        )
        assert rng.or_low is not None and rng.or_high is not None
        bar = sym.bars_5m[idx]
        setup = OrbB0Setup(
            SetupType.OPENING_RANGE_BREAKOUT,
            SetupDirection.LONG,
            SetupStatus.ENTRY_CONFIRMED,
            first + 2,
            rng.or_high,
            "CONTROL",
            stop_base=rng.or_low,
            confirmed_at_index=idx,
            confirm_close=bar.close,
            range_high=rng.or_high,
            range_low=rng.or_low,
        )
        lv = b0_levels(bar.close, rng.or_low, params, sym.tick)
        sig = SignalResult(
            Signal.ENTRY_CONFIRMED, ScoredSetup(setup, None, lv), (), bar.end, bar.end + (bar.end - bar.start)
        )
        return replace(base, signal=sig)

    run.strategy_id = "orb_b0"  # type: ignore[attr-defined]
    return run


def simulate_control_set(
    cs: ControlSet,
    sessions: Sequence[SessionInput],
    params: RulesetParams,
    experiment: str,
    capital: Decimal,
    engine_version: str,
    data_source: str,
    universe: str,
    slippage: object,
    reference: B0Reference,
    *,
    tie_break_seed: int = 1,
) -> BacktestResult:
    """Replay one control set with the ORB run's own configuration and the same reference evidence (the
    B0 contract is enforced by `BacktestConfig`). Not called by any test on real data."""
    forced = {(e.symbol, e.day): e.bar_index for e in cs.entries}
    keep: list[SessionInput] = []
    for s in sessions:
        syms = [x for x in s.symbols if (x.symbol, s.spec.session_date) in forced]
        if syms:
            keep.append(SessionInput(s.spec, syms))
    cfg = strategy_config(
        "orb_b0",
        experiment,
        params,
        capital,
        CostSchedule(),
        engine_version,
        data_source,
        universe,
        tie_break_seed=tie_break_seed,
        purpose="CONTROL",
        slippage=slippage,  # type: ignore[arg-type]
        reference_data=dict(reference.hashes),  # the B0 contract applies to controls as to ORB
        b0_context=reference.context,
    )
    return run_backtest(keep, cfg, forced_analyse(forced))


# ------------------------------------------------ balance checks (plan §4.2, before any result)


@dataclass(frozen=True, slots=True)
class BalanceReport:
    counts_identical: bool
    max_cdf_gap_pooled: Decimal
    max_cdf_gap_by_quarter: dict[str, Decimal]
    stop_median_ratio: Decimal | None
    flags: tuple[str, ...]


def _cdf_gap(a: Sequence[time], b: Sequence[time]) -> Decimal:
    if not a or not b:
        return Decimal(1) if (a or b) else Decimal(0)
    grid = sorted(set(a) | set(b))
    ca = cb = 0
    ia = ib = 0
    sa, sb = sorted(a), sorted(b)
    gap = Decimal(0)
    for t in grid:
        while ia < len(sa) and sa[ia] <= t:
            ia += 1
        while ib < len(sb) and sb[ib] <= t:
            ib += 1
        ca, cb = ia, ib
        gap = max(gap, abs(Decimal(ca) / len(sa) - Decimal(cb) / len(sb)))
    return gap


def _median(xs: Sequence[Decimal]) -> Decimal:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def balance_report(
    orb: Sequence[OrbSignal],
    control_times: Sequence[OrbSignal],
    orb_stop_pct: Sequence[Decimal],
    control_stop_pct: Sequence[Decimal],
) -> BalanceReport:
    """Counts per instrument-month identical; signal-time CDF gap at most 0.01 pooled and 0.03 per quarter;
    median stop distance within 25% (flag only). `control_times` carries the control's signal bars."""

    def counts(xs: Sequence[OrbSignal]) -> dict[tuple[str, int, int], int]:
        d: dict[tuple[str, int, int], int] = defaultdict(int)
        for x in xs:
            d[(x.symbol, x.day.year, x.day.month)] += 1
        return dict(d)

    identical = counts(orb) == counts(control_times)
    pooled = _cdf_gap([o.signal_time for o in orb], [c.signal_time for c in control_times])
    quarters: dict[str, Decimal] = {}
    keys = sorted({f"{o.day.year}Q{(o.day.month - 1) // 3 + 1}" for o in orb})
    for q in keys:
        oq = [o.signal_time for o in orb if f"{o.day.year}Q{(o.day.month - 1) // 3 + 1}" == q]
        cq = [c.signal_time for c in control_times if f"{c.day.year}Q{(c.day.month - 1) // 3 + 1}" == q]
        quarters[q] = _cdf_gap(oq, cq)
    ratio = None
    flags: list[str] = []
    if orb_stop_pct and control_stop_pct:
        mo, mc = _median(orb_stop_pct), _median(control_stop_pct)
        ratio = mc / mo if mo else None
        if ratio is not None and abs(ratio - 1) > Decimal("0.25"):
            flags.append("STOP_DISTANCE_MEDIAN_DIFFERS_OVER_25PCT")
    if not identical:
        flags.append("COUNTS_NOT_IDENTICAL")
    if pooled > Decimal("0.01"):
        flags.append("CDF_GAP_POOLED_OVER_0.01")
    if any(g > Decimal("0.03") for g in quarters.values()):
        flags.append("CDF_GAP_QUARTER_OVER_0.03")
    return BalanceReport(identical, pooled, quarters, ratio, tuple(flags))


def control_signals(cs: ControlSet, candidates: Sequence[ControlCandidate]) -> list[OrbSignal]:
    by = {(c.sym.symbol, c.day): c for c in candidates}
    out = []
    for e in cs.entries:
        c = by[(e.symbol, e.day)]
        out.append(OrbSignal(e.symbol, e.day, c.sym.bars_5m[e.bar_index].end.astimezone(IST).time()))
    return out
