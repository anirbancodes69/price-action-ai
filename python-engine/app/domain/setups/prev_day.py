"""PREV_DAY_HIGH_BREAK (long) and PREV_DAY_LOW_BREAK (short, informational) (TRD-04 §4)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.domain.setups.common import after_cutoff, bb, choch_against, confirm, htf_against, replay_simple
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.types import PivotKind


def session_swing_low_below(ctx: SetupContext, entry: Decimal, at_index: int) -> Decimal:
    """Latest confirmed session 5m swing low below `entry`, else the session low so far (TRD-04 §4)."""
    for p in reversed(ctx.pivots_5m):
        if (
            p.kind is PivotKind.LOW
            and p.index >= ctx.first
            and p.confirmed_at_index <= at_index
            and p.price < entry
        ):
            return p.price
    return min(b.low for b in ctx.bars[ctx.first : at_index + 1])


def detect_prev_day(ctx: SetupContext) -> tuple[list[Setup], list[str]]:
    out: list[Setup] = []
    reasons: list[str] = []
    for direction in (SetupDirection.LONG, SetupDirection.SHORT):
        long = direction is SetupDirection.LONG
        level = ctx.levels.pdh if long else ctx.levels.pdl
        if level is None:
            reasons.append("MISSING_CONTEXT")
            continue
        open_ = ctx.bars[ctx.first].open
        if (open_ >= level) if long else (open_ <= level):
            reasons.append("OPENED_ABOVE_LEVEL" if long else "OPENED_BELOW_LEVEL")
            continue
        s = _detect_one(ctx, direction, level)
        if s is not None:
            out.append(s)
    return out, reasons


def _detect_one(ctx: SetupContext, direction: SetupDirection, level: Decimal) -> Setup | None:
    long = direction is SetupDirection.LONG
    prox = ctx.params.pct("zone.proximity_pct")
    b = bb(ctx)
    for a in range(ctx.first, ctx.t + 1):
        if after_cutoff(ctx, a):
            return None
        close = ctx.bars[a].close
        near = close >= level * (1 - prox) if long else close <= level * (1 + prox)
        if not near or htf_against(ctx, a, direction) or choch_against(ctx, a, direction):
            continue
        s = Setup(
            SetupType.PREV_DAY_HIGH_BREAK if long else SetupType.PREV_DAY_LOW_BREAK,
            direction,
            SetupStatus.AWAITING_CONFIRMATION,
            a,
            level,
            "PDH" if long else "PDL",
        )
        beyond = close > level * (1 + b) if long else close < level * (1 - b)
        s = confirm(s, a, close) if beyond else replay_simple(ctx, s, a + 1, structure_invalidation=True)
        ref = s.confirmed_at_index or s.ended_at_index or ctx.t
        entry = s.confirm_close if s.confirm_close is not None else level
        if long:
            return replace(s, stop_base=session_swing_low_below(ctx, entry, ref))
        return s
    return None
