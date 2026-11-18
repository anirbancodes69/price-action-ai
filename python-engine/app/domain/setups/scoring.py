"""Price Action Quality Score `paqs-intraday-0.1.0` (TRD-04 §10). Rule conformance, not a probability."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.levels import TradeLevels
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.types import Bar, Direction, StructureState
from app.domain.zones import Zone

VERSION = "paqs-intraday-0.1.0"
# TRD-04 §10 constants (HYPOTHESIS, bound to the score version, not registry keys).
PDH_ANCHOR_PTS, OR_HIGH_ANCHOR_PTS, CONFLUENCE_PTS, LEVEL_CAP = 16, 14, 4, 20
TOP_FRACTION = Decimal("0.7")  # "top 30% of its range"
OR_WIDTH_OK = (Decimal("0.50"), Decimal("1.50"))
OR_CONFIRM_WITHIN_BARS = 24
PDH_OPEN_GAP_PCT = Decimal("0.30")
RETEST_WITHIN_BARS = 3


@dataclass(frozen=True, slots=True)
class Component:
    name: str
    points: int
    maximum: int
    missing: bool = False
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Paqs:
    version: str
    total: int
    components: tuple[Component, ...]


def structure_points(htf: StructureState | None, htf_dir: Direction | None, s5: StructureState) -> int:
    """TRD-04 §10 structure alignment (25)."""
    if htf is None:
        return 0
    up = htf is StructureState.BULLISH
    soft = htf is StructureState.SIDEWAYS or (htf is StructureState.TRANSITION and htf_dir is Direction.UP)
    if up and s5 is StructureState.BULLISH:
        return 25
    if up:
        return 18
    if soft and s5 is StructureState.BULLISH:
        return 15
    return 8 if soft else 0  # against: 0 (only the sweep setup may be penalised instead of blocked)


def rr_points(rr: Decimal | None, min_rr: Decimal) -> int:
    if rr is None:
        return 0
    if rr >= 3:
        return 10
    if rr >= Decimal("2.5"):
        return 8
    return 6 if rr >= min_rr else 0


def in_top_part(bar: Bar) -> bool:
    """Close in the top 30% of the bar's range (a zero-range bar does not count)."""
    rng = bar.high - bar.low
    return rng > 0 and bar.close >= bar.low + TOP_FRACTION * rng


def entry_points(s: Setup, bars: Sequence[Bar]) -> int:
    if s.status is SetupStatus.FORMING:
        return 0
    if s.status is SetupStatus.AWAITING_CONFIRMATION:
        return 8
    if s.confirmed_at_index is None:
        return 0
    b = bars[s.confirmed_at_index]
    return 20 if b.close >= (b.high + b.low) / 2 else 15


def _confluent(level: Decimal, zones: Sequence[Zone], tolerance: Decimal) -> bool:
    return any(z.low * (1 - tolerance) <= level <= z.high * (1 + tolerance) for z in zones)


def level_component(s: Setup, ctx: SetupContext, zones: Sequence[Zone]) -> Component:
    if s.anchor == "ZONE":
        if s.zone is None:
            return Component("key_level_quality", 0, 20, True, "zone anchor unavailable")
        return Component(
            "key_level_quality", int((Decimal(s.zone.strength) * Decimal("0.2")).quantize(Decimal(1))), 20
        )
    base = PDH_ANCHOR_PTS if s.anchor == "PDH" else OR_HIGH_ANCHOR_PTS
    level = ctx.levels.pdh if s.anchor == "PDH" else ctx.levels.or_high
    if level is not None and _confluent(level, zones, ctx.params.pct("zone.cluster_tolerance_pct")):
        base += CONFLUENCE_PTS
    return Component("key_level_quality", min(base, LEVEL_CAP), 20)


def checklist_component(s: Setup, ctx: SetupContext) -> Component:
    first = ctx.first
    ref = s.confirmed_at_index
    pts = 0
    if s.type is SetupType.OPENING_RANGE_BREAKOUT:
        if s.width_pct is not None and OR_WIDTH_OK[0] <= s.width_pct <= OR_WIDTH_OK[1]:
            pts += 9
        if ref is not None and in_top_part(ctx.bars[ref]):
            pts += 8
        if ref is not None and ref - first <= OR_CONFIRM_WITHIN_BARS:
            pts += 8
    elif s.type is SetupType.PREV_DAY_HIGH_BREAK:
        pdh = ctx.levels.pdh
        if pdh is not None and (pdh - ctx.bars[first].open) / pdh * 100 >= PDH_OPEN_GAP_PCT:
            pts += 8
        if ref is not None and in_top_part(ctx.bars[ref]):
            pts += 9
        if ref is not None and ctx.structure.states[ref].state is StructureState.BULLISH:
            pts += 8
    elif s.type is SetupType.BREAKOUT_RETEST:
        if s.breakout_index is not None and in_top_part(ctx.bars[s.breakout_index]):
            pts += 8
        if s.retest_closes_hold:
            pts += 9
        if (
            s.retest_index is not None
            and s.breakout_index is not None
            and s.retest_index - s.breakout_index <= RETEST_WITHIN_BARS
        ):
            pts += 8
    return Component("setup_quality", pts, 25)


def score_setup(
    s: Setup, ctx: SetupContext, zones: Sequence[Zone], levels: TradeLevels | None
) -> Paqs | None:
    """`None` for informational (SHORT) setups: they are not scored."""
    if s.direction is not SetupDirection.LONG:
        return None
    r = s.confirmed_at_index if s.confirmed_at_index is not None else s.ended_at_index or ctx.t
    h = ctx.htf[r].state
    structure = Component(
        "structure_alignment",
        structure_points(
            h.state if h else None, h.transition_direction if h else None, ctx.structure.states[r].state
        ),
        25,
        h is None,
        "no 15m context" if h is None else None,
    )
    rr_missing = levels is None or levels.rr is None
    rr = Component(
        "risk_reward",
        rr_points(levels.rr if levels else None, ctx.params.decimal("risk.min_rr")),
        10,
        rr_missing,
        "no target or stop" if rr_missing else None,
    )
    comps = (
        structure,
        level_component(s, ctx, zones),
        checklist_component(s, ctx),
        Component("entry_confirmation", entry_points(s, ctx.bars), 20),
        rr,
    )
    return Paqs(VERSION, sum(c.points for c in comps), comps)  # not re-normalised when a component is missing
