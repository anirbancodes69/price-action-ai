"""Orchestration: snapshot check, structure on 5m and 15m, alignment, session levels (ENG-04 §4).

Setups, zones and risk arrive in later milestones (I4, I5).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.candles import candles_hash
from app.domain.htf import HtfContext, align_htf
from app.domain.liquidity import LiquidityPool, equal_levels
from app.domain.params import RulesetParams
from app.domain.pivots import detect_pivots, label_pivots
from app.domain.session import DailyLevels, SessionLevels, session_levels
from app.domain.snapshot import SnapshotCheck, SnapshotStatus, check_snapshot
from app.domain.structure import run_structure
from app.domain.types import Bar, StructureResult, Timeframe
from app.domain.zone_build import build_zones
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
) -> AnalysisResult:
    """Pure function of closed bars and the ruleset (bars span `analysis.lookback_sessions` sessions)."""
    check = check_snapshot(bars_5m, bars_15m, params)
    h5, h15 = candles_hash(bars_5m), candles_hash(bars_15m)
    if check.status is not SnapshotStatus.VALID:
        return AnalysisResult(params.code, params.version, check, h5, h15, None, None, None, None)
    s5 = _structure(bars_5m, "5m", params)
    s15 = _structure(bars_15m, "15m", params)
    htf = align_htf([bars_5m[-1].end], bars_15m, s15)[0]
    levels = session_levels(bars_5m, session_open, prev_day, params.int_("session.opening_range_minutes"))
    t = len(bars_5m) - 1
    zones = build_zones(bars_5m, s5.pivots, s15.pivots, t, params, session_open, previous_session_open, tick)
    pools = equal_levels(bars_5m, s5.pivots, t, params.equal_tolerance())
    return AnalysisResult(
        params.code, params.version, check, h5, h15, s5, s15, htf, levels, tuple(zones), tuple(pools)
    )
