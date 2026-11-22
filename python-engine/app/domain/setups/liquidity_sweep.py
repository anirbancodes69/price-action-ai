"""LIQUIDITY_SWEEP_REVERSAL, long (TRD-04 §7). Disabled unless the ruleset enables it (`pa-intraday 0.2.0`).

Price runs below an obvious liquidity level `Y` with a wick and reclaims it. A level is known before bar `w`
and unbroken (no close below `Y x (1 - sbuf)` since it formed). Sweep bar `w`: `L[w] < Y x (1 - sbuf)` and
the reclaim is the same bar (`C[w] ≥ Y`) or the next one (`C[w] < Y`, `C[w] ≥ Y x (1 - sbuf)`, `C[w+1] ≥ Y`,
`L[w+1] ≥ L[w] x (1 - sbuf)`). A close of `w` below `Y x (1 - sbuf)` is a structural break, not a sweep.

Implementation choices where TRD-04 is silent (OQ-SD-08): one setup per sweep bar, for the highest level
reclaimed on it (ties by anchor order); a level is used once per session (SD-04).
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.params import RulesetParams
from app.domain.setups.common import after_cutoff, replay_simple
from app.domain.setups.support_levels import ANCHOR_ORDER, support_levels, zone_levels
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.zones import Zone

ENABLED_KEY = "setup.liquidity_sweep_enabled"


def liquidity_sweep_enabled(params: RulesetParams) -> bool:
    """A ruleset without the key (`pa-intraday 0.1.0`) has the setup disabled (TV-SET-19)."""
    return params.values.get(ENABLED_KEY) is True


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
    levels = support_levels(ctx, sbuf)
    taken: set[tuple[str, Decimal]] = set()
    out: list[Setup] = []
    for w in range(max(ctx.first, 1), ctx.t + 1):
        if after_cutoff(ctx, w):
            break
        cands: list[tuple[Decimal, int, str, Zone | None]] = []
        for lv in levels:
            if lv.known_from < w and (lv.first_break is None or lv.first_break >= w):
                cands.append((lv.price, ANCHOR_ORDER.index(lv.anchor), lv.anchor, None))
        for price, z in zone_levels(ctx, w):
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
