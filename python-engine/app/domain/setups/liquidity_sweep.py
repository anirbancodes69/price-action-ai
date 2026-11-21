"""LIQUIDITY_SWEEP_REVERSAL, long (TRD-04 §7). Disabled unless the ruleset enables it (`pa-intraday 0.2.0`).

Price runs below an obvious liquidity level `Y` with a wick and reclaims it. A level is known before bar `w`
and unbroken (no close below `Y x (1 - sbuf)` since it formed). Sweep bar `w`: `L[w] < Y x (1 - sbuf)` and
the reclaim is the same bar (`C[w] ≥ Y`) or the next one (`C[w] < Y`, `C[w] ≥ Y x (1 - sbuf)`, `C[w+1] ≥ Y`,
`L[w+1] ≥ L[w] x (1 - sbuf)`). A close of `w` below `Y x (1 - sbuf)` is a structural break, not a sweep.

Implementation choices where TRD-04 is silent (OQ-SD-08): one setup per sweep bar, for the highest level
reclaimed on it (ties by anchor order); a level is used once per session (SD-04).
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal

from app.domain.liquidity import PoolType, equal_levels
from app.domain.params import RulesetParams
from app.domain.setups.common import after_cutoff, or_end, replay_simple
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.types import PivotKind
from app.domain.zone_build import build_zones, zone_role
from app.domain.zones import Zone, ZoneRole, ZoneStatus

ENABLED_KEY = "setup.liquidity_sweep_enabled"
# Tie-break between levels with the same price on one sweep bar.
ANCHOR_ORDER = ("PDL", "OR_LOW", "EQUAL_LOWS", "ZONE", "SWING_LOW_5M", "SWING_LOW_15M")


def liquidity_sweep_enabled(params: RulesetParams) -> bool:
    """A ruleset without the key (`pa-intraday 0.1.0`) has the setup disabled (TV-SET-19)."""
    return params.values.get(ENABLED_KEY) is True


@dataclass(frozen=True, slots=True)
class _Level:
    anchor: str
    price: Decimal
    known_from: int  # exists for sweep bars `w > known_from`
    first_break: int | None  # first bar whose close is below `price x (1 - sbuf)` after it formed


def _first_break(ctx: SetupContext, price: Decimal, start: int, sbuf: Decimal) -> int | None:
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


def _levels(ctx: SetupContext, sbuf: Decimal) -> list[_Level]:
    """Every liquidity level of the session except zones (those depend on the sweep bar: `_zone_levels`)."""
    out: list[_Level] = []

    def add(anchor: str, price: Decimal, known_from: int, scan_from: int) -> None:
        brk = _first_break(ctx, price, scan_from, sbuf)
        out.append(_Level(anchor, price, known_from, brk))

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


def _zone_levels(ctx: SetupContext, w: int) -> list[tuple[Decimal, Zone]]:
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


def _reclaim(ctx: SetupContext, w: int, y: Decimal, sbuf: Decimal) -> tuple[int, Decimal, bool] | None:
    """`(reclaim bar index, sweep_low, same_bar)` when bar `w` sweeps `y` and it is reclaimed, else None."""
    bars = ctx.bars
    swept_below = y * (1 - sbuf)
    if not bars[w].low < swept_below:
        return None
    if bars[w].close >= y:
        return w, bars[w].low, True
    if bars[w].close < swept_below or w + 1 > ctx.t:
        return None  # a structural break (TRD-02 §8), or the reclaim bar has not closed yet
    nxt = bars[w + 1]
    if nxt.close >= y and nxt.low >= bars[w].low * (1 - sbuf):
        return w + 1, min(bars[w].low, nxt.low), False
    return None


def detect_liquidity_sweep(ctx: SetupContext) -> tuple[list[Setup], list[str]]:
    if not liquidity_sweep_enabled(ctx.params):
        return [], []
    sbuf = ctx.params.pct("structure.break_buffer_pct_5m")
    levels = _levels(ctx, sbuf)
    taken: set[tuple[str, Decimal]] = set()
    out: list[Setup] = []
    for w in range(max(ctx.first, 1), ctx.t + 1):
        if after_cutoff(ctx, w):
            break
        cands: list[tuple[Decimal, int, str, Zone | None]] = []
        for lv in levels:
            if lv.known_from < w and (lv.first_break is None or lv.first_break >= w):
                cands.append((lv.price, ANCHOR_ORDER.index(lv.anchor), lv.anchor, None))
        for price, z in _zone_levels(ctx, w):
            cands.append((price, ANCHOR_ORDER.index("ZONE"), "ZONE", z))
        for price, _, anchor, zone in sorted(cands, key=lambda c: (-c[0], c[1])):
            if (anchor, price) in taken:
                continue
            hit = _reclaim(ctx, w, price, sbuf)
            if hit is None:
                continue
            r, sweep_low, same_bar = hit
            if after_cutoff(ctx, r):
                continue
            taken.add((anchor, price))
            s = Setup(
                SetupType.LIQUIDITY_SWEEP_REVERSAL,
                SetupDirection.LONG,
                SetupStatus.AWAITING_CONFIRMATION,
                r,
                ctx.bars[r].high,
                anchor,
                stop_base=sweep_low,
                zone=zone,
                swept_level=price,
                sweep_low=sweep_low,
                same_bar_reclaim=same_bar,
            )
            out.append(
                replay_simple(
                    ctx, s, r + 1, invalid_close=("SWEEP_FAILED", sweep_low, True), htf_blocks=False
                )
            )
            break  # one setup per sweep bar
    return out, []
