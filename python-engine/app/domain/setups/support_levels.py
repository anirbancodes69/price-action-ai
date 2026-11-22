"""Support-level facts shared by the failed-reversal strategies (Strategies 01 and 02).

The liquidity levels `Y` below price where long stops or buyers sit: 5m and 15m confirmed swing lows,
`EQUAL_LOWS` pools, `PDL`, `OR_LOW` (this module) and active support zones (`zone_levels`). Each level carries
the bar from which it is known and the first close below `Y x (1 - sbuf)`, so a strategy can say "unbroken
before bar `x`" (sweep) or "broken by the close of bar `x`" (failed breakdown) without recomputing it.
Neutral facts only: no strategy rule lives here, and nothing here depends on a strategy.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal

from app.domain.liquidity import PoolType, equal_levels
from app.domain.setups.common import or_end
from app.domain.setups.types import SetupContext
from app.domain.types import PivotKind
from app.domain.zone_build import build_zones, zone_role
from app.domain.zones import Zone, ZoneRole, ZoneStatus

# Tie-break between levels with the same price on one sweep bar.
ANCHOR_ORDER = ("PDL", "OR_LOW", "EQUAL_LOWS", "ZONE", "SWING_LOW_5M", "SWING_LOW_15M")


@dataclass(frozen=True, slots=True)
class Level:
    anchor: str
    price: Decimal
    known_from: int  # exists for bars `w > known_from`
    first_break: int | None  # first bar whose close is below `price x (1 - sbuf)` after it formed


def first_break(ctx: SetupContext, price: Decimal, start: int, sbuf: Decimal) -> int | None:
    """Index of the first close below `price x (1 - sbuf)` from `start` to `t`, or None."""
    limit = price * (1 - sbuf)
    start = max(start, 0)
    # The history before the session is checked in one pass in C; only the session bars are walked.
    pre_end = max(ctx.first, start)
    if start < pre_end and min(b.close for b in ctx.bars[start:pre_end]) < limit:
        return next(j for j in range(start, pre_end) if ctx.bars[j].close < limit)
    for j in range(pre_end, ctx.t + 1):
        if ctx.bars[j].close < limit:
            return j
    return None


def support_levels(ctx: SetupContext, sbuf: Decimal) -> list[Level]:
    """Every level of the session except zones (those depend on the bar being tested: `zone_levels`)."""
    out: list[Level] = []

    def add(anchor: str, price: Decimal, known_from: int, scan_from: int) -> None:
        brk = first_break(ctx, price, scan_from, sbuf)
        out.append(Level(anchor, price, known_from, brk))

    for p in ctx.pivots_5m:
        if p.kind is PivotKind.LOW and p.confirmed_at_index <= ctx.t:
            add("SWING_LOW_5M", p.price, p.confirmed_at_index, p.index + 1)
    starts = [b.start for b in ctx.bars]
    ends = [b.end for b in ctx.bars]
    for p in ctx.pivots_15m:
        if p.kind is PivotKind.LOW and p.confirmed_at <= ends[ctx.t]:
            known = bisect_left(ends, p.confirmed_at)  # first 5m bar ending at or after the confirmation
            add("SWING_LOW_15M", p.price, known, bisect_left(starts, p.bar_start))
    pools = ctx.pools
    if pools is None:
        pools = equal_levels(ctx.bars, ctx.pivots_5m, ctx.t, ctx.params.equal_tolerance())
    for pool in pools:
        if pool.type is PoolType.EQUAL_LOWS and pool.confirmed_at_index <= ctx.t:
            add("EQUAL_LOWS", pool.level, pool.confirmed_at_index, pool.second_index + 1)
    if ctx.levels.pdl is not None:
        add("PDL", ctx.levels.pdl, ctx.first - 1, ctx.first)
    if ctx.levels.or_low is not None:
        o = next((j for j in range(ctx.first, ctx.t + 1) if ctx.bars[j].end >= or_end(ctx)), None)
        if o is not None:
            add("OR_LOW", ctx.levels.or_low, o, o + 1)
    return out


def zone_levels(ctx: SetupContext, w: int) -> list[tuple[Decimal, Zone]]:
    """`Z.low` of the active support zones known at the close of bar `w - 1`."""
    if w < 1:
        return []
    build = ctx.zone_cache.zones if ctx.zone_cache is not None else build_zones
    zones = build(
        ctx.bars,
        ctx.pivots_5m,
        ctx.pivots_15m,
        w - 1,
        ctx.params,
        ctx.session_open,
        ctx.previous_session_open,
        ctx.tick,
    )
    close = ctx.bars[w - 1].close
    return [
        (z.low, z) for z in zones if z.status is ZoneStatus.ACTIVE and zone_role(z, close) is ZoneRole.SUPPORT
    ]
