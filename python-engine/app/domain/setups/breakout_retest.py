"""BREAKOUT_RETEST, long (TRD-04 §5). The short mirror is not implemented yet."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.domain.setups.common import after_cutoff, bb, choch_against, confirm, end, end_of_life, or_end
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.types import Direction
from app.domain.zone_break import evaluate_break
from app.domain.zone_build import build_zones, zone_role
from app.domain.zones import Zone, ZoneRole, ZoneStatus


def _level_zone(level: Decimal, min_width: Decimal) -> tuple[Decimal, Decimal]:
    """A reference level as a zone of minimum width around it (TRD-04 §5)."""
    half = level * min_width / 2
    return level - half, level + half


def _anchors(ctx: SetupContext) -> list[tuple[str, Zone | None, Decimal, Decimal, int]]:
    """Level anchors known at session start / opening-range completion: (name, zone, low, high, formed)."""
    mw = ctx.params.pct("zone.min_width_pct")
    out: list[tuple[str, Zone | None, Decimal, Decimal, int]] = []
    if ctx.levels.pdh is not None:
        lo, hi = _level_zone(ctx.levels.pdh, mw)
        out.append(("PDH", None, lo, hi, ctx.first - 1))
    if ctx.levels.or_high is not None:
        lo, hi = _level_zone(ctx.levels.or_high, mw)
        o = next((j for j in range(ctx.first, ctx.t + 1) if ctx.bars[j].end >= or_end(ctx)), ctx.t)
        out.append(("OR_HIGH", None, lo, hi, o))
    return out


def detect_breakout_retest(ctx: SetupContext) -> tuple[list[Setup], list[str]]:
    p = ctx.params
    confirm_closes = p.int_("zone.break_confirm_closes")
    b = bb(ctx)
    out: list[Setup] = []
    taken: set[str] = set()  # level anchors already used (SD-04, one per session)
    used_zones: list[tuple[Decimal, Decimal]] = []

    for j in range(ctx.first, ctx.t + 1):
        if after_cutoff(ctx, j):
            break
        cands: list[tuple[str, Zone | None, Decimal, Decimal, int]] = [
            a for a in _anchors(ctx) if a[0] not in taken and a[4] < j
        ]
        if j >= 1:
            for z in build_zones(
                ctx.bars,
                ctx.pivots_5m,
                ctx.pivots_15m,
                j - 1,
                p,
                ctx.session_open,
                ctx.previous_session_open,
                ctx.tick,
            ):
                if (
                    z.status is ZoneStatus.ACTIVE
                    and z.touches >= 2
                    and zone_role(z, ctx.bars[j - 1].close) is not ZoneRole.SUPPORT
                    and not any(z.low <= uh and uz <= z.high for uz, uh in used_zones)
                ):
                    cands.append(("ZONE", z, z.low, z.high, z.formed_at_index))
        for name, zone, lo, hi, formed in cands:
            r = evaluate_break(ctx.bars, lo, hi, formed, j, confirm_closes, b, Direction.UP)
            if not (
                r.status is ZoneStatus.BROKEN_FLIPPED
                and r.broken_direction is Direction.UP
                and r.broken_at_index == j
            ):
                continue
            if name == "ZONE":
                used_zones.append((lo, hi))
            else:
                taken.add(name)
            pseudo = zone if zone is not None else Zone(lo, hi, (), formed)
            out.append(_replay(ctx, name, pseudo, lo, hi, j))
    return out, []


def _replay(ctx: SetupContext, anchor: str, zone: Zone, lo: Decimal, hi: Decimal, b_idx: int) -> Setup:
    p = ctx.params
    b = bb(ctx)
    rt = p.pct("setup.retest_tolerance_pct")
    wait = p.int_("setup.max_retest_wait_bars")
    s = Setup(
        SetupType.BREAKOUT_RETEST,
        SetupDirection.LONG,
        SetupStatus.FORMING,
        b_idx,
        hi,
        anchor,
        zone=zone,
        breakout_index=b_idx,
    )
    retest_low: Decimal | None = None
    holds = True
    for j in range(b_idx + 1, ctx.t + 1):
        stop = end_of_life(ctx, s, j)
        if stop:
            return end(s, stop[0], stop[1], j)
        bar = ctx.bars[j]
        if bar.close < lo * (1 - b):
            return end(s, SetupStatus.INVALIDATED, "FAILED_BREAKOUT", j)
        if choch_against(ctx, j, SetupDirection.LONG):
            return end(s, SetupStatus.INVALIDATED, "STRUCTURE_INVALIDATED", j)
        if s.status is SetupStatus.AWAITING_CONFIRMATION and bar.close > s.trigger_price * (1 + b):
            return confirm(s, j, bar.close)
        if s.status is SetupStatus.FORMING and j > b_idx + wait:
            return end(s, SetupStatus.EXPIRED, "NO_RETEST", j)
        if bar.low <= hi * (1 + rt) and bar.close >= lo:
            retest_low = bar.low if retest_low is None else min(retest_low, bar.low)
            holds = holds and bar.close >= hi
            s = replace(
                s,
                status=SetupStatus.AWAITING_CONFIRMATION,
                trigger_price=bar.high,
                retest_index=s.retest_index if s.retest_index is not None else j,
                retest_closes_hold=holds,
                stop_base=min(retest_low, lo),
            )
    return s
