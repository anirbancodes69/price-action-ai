"""OPENING_RANGE_BREAKOUT and its informational mirror (TRD-04 §3)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.setups.common import after_cutoff, bb, htf_against, or_end, replay_simple
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType


def detect_opening_range(ctx: SetupContext) -> tuple[list[Setup], list[str]]:
    """Returns `(setups, no_setup_reasons)`.

    The range is complete at the first bar ending at/after `session_open + session.opening_range_minutes`.
    """
    hi, lo = ctx.levels.or_high, ctx.levels.or_low
    if hi is None or lo is None:
        return [], []
    end_ = or_end(ctx)
    o = next((j for j in range(ctx.first, ctx.t + 1) if ctx.bars[j].end >= end_), None)
    if o is None:
        return [], []
    width = (hi - lo) / lo * 100
    if width < ctx.params.decimal("setup.opening_range_min_pct"):
        return [], ["OR_TOO_NARROW"]
    if width > ctx.params.decimal("setup.opening_range_max_pct"):
        return [], ["OR_TOO_WIDE"]
    if after_cutoff(ctx, o):
        return [], []

    b = bb(ctx)
    out: list[Setup] = []
    for direction in (SetupDirection.LONG, SetupDirection.SHORT):
        if htf_against(ctx, o, direction):
            continue
        long = direction is SetupDirection.LONG
        s = Setup(
            SetupType.OPENING_RANGE_BREAKOUT,
            direction,
            SetupStatus.AWAITING_CONFIRMATION,
            o,
            hi if long else lo,
            "OR_HIGH" if long else "OR_LOW",
            stop_base=lo if long else hi,
            width_pct=width,
        )
        invalid: tuple[str, Decimal, bool] = (
            ("OR_LOW_BROKEN", lo * (1 - b), True) if long else ("OR_HIGH_BROKEN", hi * (1 + b), False)
        )
        out.append(replay_simple(ctx, s, o + 1, invalid_close=invalid))
    return out, []
