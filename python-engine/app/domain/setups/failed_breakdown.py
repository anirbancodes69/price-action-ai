"""FAILED_BREAKDOWN_RECLAIM, long (Strategy 02 specification, TRD-04 §7A).

Disabled unless the ruleset enables it (`pa-intraday 0.4.0`). Price closes below a support level `Y`
(breakdown bar `b`: `C[b] < Y x (1 - sbuf)`, no earlier close below since the level formed), then closes
back at or above it within `N = setup.failed_break_max_bars` bars (reclaim bar `r`: the first `r` with
`b < r <= b + N` and `C[r] >= Y`). `break_low = min(L[b..r])` is the stop base and `H[r]` the trigger.
A wick below `Y` that closes at or above `Y x (1 - sbuf)` is not a breakdown: that is Strategy 01's event,
so the two are disjoint.

Implementation choices (specification §7): one setup per breakdown bar, for the level reclaimed first
(ties: the highest, then anchor order); a level (anchor, price) is used once per session; zone level =
`Z.low` of an `ACTIVE` support zone at the close of `b - 1`. Invalidated by a later close below
`Y x (1 - sbuf)` (`BREAK_RESUMED`).
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.params import RulesetParams
from app.domain.setups.common import after_cutoff, replay_simple
from app.domain.setups.support_levels import ANCHOR_ORDER, support_levels, zone_levels
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.zones import Zone

ENABLED_KEY = "setup.failed_breakout_enabled"
MAX_BARS_KEY = "setup.failed_break_max_bars"


def failed_breakout_enabled(params: RulesetParams) -> bool:
    """A ruleset without the key (`pa-intraday 0.1.0` to `0.3.0`) has the setup disabled."""
    return params.values.get(ENABLED_KEY) is True


def _reclaim(ctx: SetupContext, b: int, y: Decimal, window: int) -> int | None:
    """Index of the first closed bar `r` in `(b, b + window]` with `C[r] >= y`, or None."""
    for r in range(b + 1, min(b + window, ctx.t) + 1):
        if ctx.bars[r].close >= y:
            return r
    return None


def detect_failed_breakdown(ctx: SetupContext) -> tuple[list[Setup], list[str]]:
    if not failed_breakout_enabled(ctx.params):
        return [], []
    sbuf = ctx.params.pct("structure.break_buffer_pct_5m")
    window = ctx.params.int_(MAX_BARS_KEY)
    levels = support_levels(ctx, sbuf)
    taken: set[tuple[str, Decimal]] = set()
    out: list[Setup] = []
    for b in range(max(ctx.first, 1), ctx.t + 1):
        if after_cutoff(ctx, b):
            break
        close = ctx.bars[b].close
        cands: list[tuple[Decimal, int, str, Zone | None]] = []
        for lv in levels:
            # `first_break == b`: this close is the first below the level, and the level was known before `b`.
            if lv.known_from < b and lv.first_break == b:
                cands.append((lv.price, ANCHOR_ORDER.index(lv.anchor), lv.anchor, None))
        for price, z in zone_levels(ctx, b):
            if close < price * (1 - sbuf):
                cands.append((price, ANCHOR_ORDER.index("ZONE"), "ZONE", z))
        # Causal choice: the level reclaimed first wins (a later bar cannot change a setup already detected);
        # among levels reclaimed on the same bar, the highest, then the anchor order.
        hits: list[tuple[int, Decimal, int, str, Zone | None]] = []
        for price, order, anchor, zone in cands:
            if (anchor, price) in taken:
                continue
            r = _reclaim(ctx, b, price, window)
            if r is not None and not after_cutoff(ctx, r):
                hits.append((r, -price, order, anchor, zone))
        for r, neg_price, _, anchor, zone in sorted(hits, key=lambda h: h[:3])[:1]:
            price = -neg_price
            taken.add((anchor, price))
            break_low = min(x.low for x in ctx.bars[b : r + 1])
            s = Setup(
                SetupType.FAILED_BREAKDOWN_RECLAIM,
                SetupDirection.LONG,
                SetupStatus.AWAITING_CONFIRMATION,
                r,
                ctx.bars[r].high,
                anchor,
                stop_base=break_low,
                zone=zone,
                swept_level=price,
                sweep_low=break_low,
                breakdown_index=b,
            )
            out.append(
                replay_simple(
                    ctx,
                    s,
                    r + 1,
                    invalid_close=("BREAK_RESUMED", price * (1 - sbuf), True),
                    htf_blocks=False,
                )
            )
    return out, []
