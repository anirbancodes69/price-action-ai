"""Entry, stop, target ladder and risk/reward for long setups (TRD-04 §8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.types import PivotKind
from app.domain.zones import Zone


@dataclass(frozen=True, slots=True)
class TradeLevels:
    entry: Decimal
    stop: Decimal
    target: Decimal | None
    target_source: str | None
    risk_per_share: Decimal
    rr: Decimal | None
    rr_below_min: bool


def round_down(price: Decimal, tick: Decimal | None) -> Decimal:
    """Round down to the tick (stops and targets, TRD-01 §5)."""
    if tick is None:
        return price
    return (price / tick).to_integral_value(ROUND_FLOOR) * tick


def stop_price(base: Decimal, stop_buffer: Decimal, tick: Decimal | None) -> Decimal:
    """`base x (1 - sb)` rounded down to tick (conservative: wider risk)."""
    return round_down(base * (1 - stop_buffer), tick)


def pick_target(
    entry: Decimal,
    stop: Decimal,
    candidates: Sequence[tuple[str, Decimal]],
    min_rr: Decimal,
    tick: Decimal | None,
) -> tuple[Decimal | None, str | None, Decimal | None, bool]:
    """TRD-04 §8.3: the first candidate meeting `min_rr`, else the nearest one flagged `rr_below_min`.

    Candidates closer than one tick above `entry` are skipped; targets are rounded down to tick.
    Returns `(target, source, rr, rr_below_min)`; with no usable candidate `(None, None, None, True)`.
    """
    risk = entry - stop
    min_gap = tick if tick is not None else Decimal(0)
    usable = [(name, round_down(p, tick)) for name, p in candidates if p >= entry + min_gap and p > entry]
    usable = [(n, p) for n, p in usable if p > entry]
    if not usable or risk <= 0:
        return None, None, None, True
    for name, p in usable:
        rr = (p - entry) / risk
        if rr >= min_rr:
            return p, name, rr, False
    name, p = min(usable, key=lambda c: c[1])
    return p, name, (p - entry) / risk, True


def measured_move_height(ctx: SetupContext, t: int) -> Decimal | None:
    """Height of the most recent completed 5m swing leg: last confirmed swing high minus the low before it."""
    highs = [p for p in ctx.pivots_5m if p.kind is PivotKind.HIGH and p.confirmed_at_index <= t]
    if not highs:
        return None
    h = highs[-1]
    lows = [
        p
        for p in ctx.pivots_5m
        if p.kind is PivotKind.LOW and p.index < h.index and p.confirmed_at_index <= t
    ]
    if not lows:
        return None
    height = h.price - lows[-1].price
    return height if height > 0 else None


def entry_reference(s: Setup) -> Decimal:
    """SD-07: the confirmation close once confirmed, else the trigger price."""
    return s.confirm_close if s.confirm_close is not None else s.trigger_price


def trade_levels(s: Setup, ctx: SetupContext, zones: Sequence[Zone]) -> TradeLevels | None:
    """Levels for a LONG setup; `None` for informational setups or when no structural stop exists."""
    if s.direction is not SetupDirection.LONG or s.stop_base is None:
        return None
    p = ctx.params
    entry = entry_reference(s)
    stop = stop_price(s.stop_base, p.pct("risk.stop_buffer_pct"), ctx.tick)
    t = ctx.t
    cands: list[tuple[str, Decimal]] = []
    lv = ctx.levels
    if s.type is SetupType.OPENING_RANGE_BREAKOUT and lv.or_high is not None and lv.or_low is not None:
        cands.append(("MEASURED_OPENING_RANGE", lv.or_high + (lv.or_high - lv.or_low)))
    refs = [
        (n, v) for n, v in (("PDH", lv.pdh), ("SESSION_HIGH", lv.session_high), ("OR_HIGH", lv.or_high)) if v
    ]
    cands += sorted((c for c in refs if c[1] > entry), key=lambda c: c[1])
    cands += sorted((("ZONE", z.low) for z in zones if z.low > entry), key=lambda c: c[1])
    end_t = ctx.bars[t].end
    htf = [
        x.price
        for x in ctx.pivots_15m
        if x.kind is PivotKind.HIGH and x.confirmed_at <= end_t and x.price > entry
    ]
    if htf:
        cands.append(("HTF_SWING_HIGH", max(htf)))
    height = measured_move_height(ctx, t)
    if height is not None:
        anchor = s.zone.high if s.type is SetupType.BREAKOUT_RETEST and s.zone is not None else entry
        cands.append(("MEASURED_MOVE", anchor + height))
    min_rr = p.decimal("risk.min_rr")
    target, source, rr, below = pick_target(entry, stop, cands, min_rr, ctx.tick)
    status_ok = s.status in (
        SetupStatus.FORMING,
        SetupStatus.AWAITING_CONFIRMATION,
        SetupStatus.ENTRY_CONFIRMED,
    )
    return TradeLevels(entry, stop, target, source, entry - stop, rr, below) if status_ok else None
