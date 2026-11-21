"""Orchestration: snapshot check, structure on 5m and 15m, alignment, session levels (ENG-04 §4).

Setups, zones and risk arrive in later milestones (I4, I5).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from app.domain.candles import candles_hash
from app.domain.htf import HtfContext, align_htf
from app.domain.levels import trade_levels
from app.domain.liquidity import LiquidityPool, equal_levels
from app.domain.params import RulesetParams
from app.domain.pivots import detect_pivots, label_pivots
from app.domain.session import DailyLevels, SessionLevels, entry_cutoff, session_levels
from app.domain.setups.breakout_retest import detect_breakout_retest
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.prev_day import detect_prev_day
from app.domain.setups.scoring import score_setup
from app.domain.setups.signal import ScoredSetup, SignalResult, choose_signal
from app.domain.setups.types import Setup, SetupContext
from app.domain.snapshot import SnapshotCheck, SnapshotStatus, check_snapshot
from app.domain.structure import run_structure
from app.domain.types import Bar, StructureResult, Timeframe
from app.domain.zone_build import build_zones
from app.domain.zone_cache import ZoneCache
from app.domain.zones import Zone


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    ruleset_code: str
    ruleset_version: str
    check: SnapshotCheck
    input_hash_5m: str
    input_hash_15m: str
    structure_5m: StructureResult | None
    structure_15m: StructureResult | None
    htf: HtfContext | None  # 15m context at the last 5m bar
    levels: SessionLevels | None
    zones: tuple[Zone, ...] | None = None
    pools: tuple[LiquidityPool, ...] | None = None
    setups: tuple[ScoredSetup, ...] | None = None
    signal: SignalResult | None = None
    no_setup_reasons: tuple[str, ...] = ()


# A detector reads the shared facts in a `SetupContext` and returns (setups, no-setup reasons).
Detector = Callable[[SetupContext], tuple[list[Setup], list[str]]]
ALL_DETECTORS: tuple[Detector, ...] = (
    detect_opening_range,
    detect_prev_day,
    detect_breakout_retest,
    detect_liquidity_sweep,
)


def _structure(bars: Sequence[Bar], tf: Timeframe, params: RulesetParams) -> StructureResult:
    pivots = label_pivots(
        detect_pivots(bars, params.pivot_left(tf), params.pivot_right(tf)), params.equal_tolerance()
    )
    return run_structure(bars, pivots, params.break_buffer(tf))


def analyse(
    bars_5m: Sequence[Bar],
    bars_15m: Sequence[Bar],
    session_open: datetime,
    prev_day: DailyLevels | None,
    params: RulesetParams,
    previous_session_open: datetime | None = None,
    tick: Decimal | None = None,
    session_close: datetime | None = None,
    zone_cache: ZoneCache | None = None,
    detectors: Sequence[Detector] | None = None,
    isolated: bool = False,
) -> AnalysisResult:
    """Pure function of closed bars and the ruleset (bars span `analysis.lookback_sessions` sessions).

    `detectors` and `isolated` are the single-strategy run mode (backtesting standards §3). Only the
    given detectors run; with `isolated`, setups carry no PAQS and the signal does not use the score gate. The
    defaults are the live behaviour and are unchanged.
    """
    check = check_snapshot(bars_5m, bars_15m, params)
    h5, h15 = candles_hash(bars_5m), candles_hash(bars_15m)
    if check.status is not SnapshotStatus.VALID:
        return AnalysisResult(params.code, params.version, check, h5, h15, None, None, None, None)
    s5 = _structure(bars_5m, "5m", params)
    s15 = _structure(bars_15m, "15m", params)
    htf = align_htf([bars_5m[-1].end], bars_15m, s15)[0]
    levels = session_levels(bars_5m, session_open, prev_day, params.int_("session.opening_range_minutes"))
    t = len(bars_5m) - 1
    zones = (zone_cache.zones if zone_cache is not None else build_zones)(
        bars_5m, s5.pivots, s15.pivots, t, params, session_open, previous_session_open, tick
    )
    pools = equal_levels(bars_5m, s5.pivots, t, params.equal_tolerance())
    result = AnalysisResult(
        params.code, params.version, check, h5, h15, s5, s15, htf, levels, tuple(zones), tuple(pools)
    )
    first = next((i for i, b in enumerate(bars_5m) if b.start >= session_open), None)
    if session_close is None or first is None:
        return result
    ctx = SetupContext(
        bars_5m,
        first,
        t,
        session_open,
        entry_cutoff(session_close, params.int_("session.entry_cutoff_minutes_before_close")),
        levels,
        align_htf([b.end for b in bars_5m], bars_15m, s15),
        s5,
        s5.pivots,
        s15.pivots,
        previous_session_open,
        params,
        tick,
        zone_cache,
        tuple(pools),
    )
    found: list[Setup] = []
    reasons: list[str] = []
    for detect in ALL_DETECTORS if detectors is None else detectors:
        got, why = detect(ctx)
        found += got
        reasons += why
    scored = []
    for st in found:
        lv = trade_levels(st, ctx, zones)
        scored.append(ScoredSetup(st, None if isolated else score_setup(st, ctx, zones, lv), lv))
    sig = choose_signal(scored, ctx, reasons, score_gate=not isolated)
    return replace(result, setups=tuple(scored), signal=sig, no_setup_reasons=tuple(reasons))
