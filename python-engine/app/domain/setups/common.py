"""Shared lifecycle rules SD-01..SD-08 (TRD-04 §2)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus
from app.domain.types import Direction, EventType, StructureState


def or_end(ctx: SetupContext) -> datetime:
    return ctx.session_open + timedelta(minutes=ctx.params.int_("session.opening_range_minutes"))


def bb(ctx: SetupContext) -> Decimal:
    return ctx.params.pct("setup.breakout_buffer_pct")


def htf_against(ctx: SetupContext, j: int, direction: SetupDirection) -> bool:
    """SD-05. No 15m context is treated as against (conservative)."""
    s = ctx.htf[j].state
    if s is None:
        return True
    bearish = s.state is StructureState.BEARISH or (
        s.state is StructureState.TRANSITION and s.transition_direction is Direction.DOWN
    )
    bullish = s.state is StructureState.BULLISH or (
        s.state is StructureState.TRANSITION and s.transition_direction is Direction.UP
    )
    return bearish if direction is SetupDirection.LONG else bullish


def choch_against(ctx: SetupContext, j: int, direction: SetupDirection) -> bool:
    """A CHoCH on the 5m series at bar `j` against the setup (`STRUCTURE_INVALIDATED`)."""
    want = Direction.DOWN if direction is SetupDirection.LONG else Direction.UP
    return any(
        e.type is EventType.CHOCH and e.break_index == j and e.direction is want for e in ctx.structure.events
    )


def after_cutoff(ctx: SetupContext, j: int) -> bool:
    return ctx.bars[j].end > ctx.cutoff


def end_of_life(ctx: SetupContext, s: Setup, j: int) -> tuple[SetupStatus, str] | None:
    """SD-08 cutoff, SD-02 age (EXPIRED), then SD-05 (INVALIDATED), in that order."""
    if after_cutoff(ctx, j):
        return SetupStatus.EXPIRED, "SESSION_CUTOFF"
    if j - s.detected_at_index > ctx.params.int_("setup.expiry_bars"):
        return SetupStatus.EXPIRED, "AGED_OUT"
    if htf_against(ctx, j, s.direction):
        return SetupStatus.INVALIDATED, "HTF_AGAINST"
    return None


def end(s: Setup, status: SetupStatus, reason: str, j: int) -> Setup:
    return replace(s, status=status, end_reason=reason, ended_at_index=j)


def confirm(s: Setup, j: int, close: Decimal) -> Setup:
    return replace(s, status=SetupStatus.ENTRY_CONFIRMED, confirmed_at_index=j, confirm_close=close)


def replay_simple(
    ctx: SetupContext,
    s: Setup,
    start: int,
    invalid_close: tuple[str, Decimal, bool] | None = None,
    structure_invalidation: bool = False,
) -> Setup:
    """Replay bars `start..t` for a setup that is already AWAITING_CONFIRMATION.

    `invalid_close = (reason, level, close_below)`: invalidated by a close beyond `level` (SD-01: checked
    before confirmation). Confirmation: a close beyond `trigger_price` by the breakout buffer.
    """
    b = bb(ctx)
    long = s.direction is SetupDirection.LONG
    for j in range(start, ctx.t + 1):
        stop = end_of_life(ctx, s, j)
        if stop:
            return end(s, stop[0], stop[1], j)
        close = ctx.bars[j].close
        if invalid_close and (close < invalid_close[1] if invalid_close[2] else close > invalid_close[1]):
            return end(s, SetupStatus.INVALIDATED, invalid_close[0], j)
        if structure_invalidation and choch_against(ctx, j, s.direction):
            return end(s, SetupStatus.INVALIDATED, "STRUCTURE_INVALIDATED", j)
        if (close > s.trigger_price * (1 + b)) if long else (close < s.trigger_price * (1 - b)):
            return confirm(s, j, close)
    return s
