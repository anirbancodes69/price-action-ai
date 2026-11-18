"""Build zones at bar `t` and proximity (TRD-03 §2-§3, §7)."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from app.domain.params import RulesetParams
from app.domain.types import Bar, SwingPoint
from app.domain.zone_break import evaluate_break
from app.domain.zone_strength import strength_score, touch_stats
from app.domain.zones import Zone, ZoneMember, ZoneRole, ZoneStatus, cluster_pivots


def build_zones(
    bars_5m: Sequence[Bar],
    pivots_5m: Sequence[SwingPoint],
    pivots_15m: Sequence[SwingPoint],
    t: int,
    params: RulesetParams,
    current_session_open: datetime,
    previous_session_open: datetime | None,
    tick: Decimal | None = None,
) -> list[Zone]:
    """Zones known at the close of 5m bar `t`; retired zones are dropped.

    5m pivots need `confirmed_at_index <= t`. A 15m pivot is usable only when `confirmed_at <= end of
    bar t` and becomes a member at the first 5m bar ending at or after its confirmation (TV-ZON-09).
    `formed_at_index` is the latest member knowledge index among the members visible at `t`.
    """
    ends = [b.end for b in bars_5m[: t + 1]]
    starts = [b.start for b in bars_5m[: t + 1]]
    members: list[ZoneMember] = [
        ZoneMember("5m", p, p.index, p.confirmed_at_index) for p in pivots_5m if p.confirmed_at_index <= t
    ]
    for p in pivots_15m:
        if p.confirmed_at <= ends[t]:
            known = bisect_left(ends, p.confirmed_at)
            members.append(ZoneMember("15m", p, min(bisect_left(starts, p.bar_start), known), known))

    confirm = params.int_("zone.break_confirm_closes")
    buf = params.pct("setup.breakout_buffer_pct")
    window = params.pivot_right("5m")
    zones: list[Zone] = []
    for c in cluster_pivots(
        members, params.pct("zone.cluster_tolerance_pct"), params.pct("zone.min_width_pct"), tick
    ):
        formed = max(m.known_index_5m for m in c.members)
        out = evaluate_break(bars_5m, c.low, c.high, formed, t, confirm, buf)
        if out.status is ZoneStatus.RETIRED:
            continue
        stats = touch_stats(bars_5m, c.members, c.low, c.high, formed, t, window)
        flipped = out.status is not ZoneStatus.ACTIVE
        score, bucket = strength_score(
            stats,
            current_session_open,
            previous_session_open,
            any(m.timeframe == "15m" for m in c.members),
            flipped,
        )
        zones.append(
            Zone(
                c.low,
                c.high,
                c.members,
                formed,
                out.status,
                out.broken_direction,
                out.broken_at_index,
                out.retired_at_index,
                stats.touches,
                score,
                bucket,
            )
        )
    return zones


def zone_role(zone: Zone, close: Decimal) -> ZoneRole:
    """TRD-03 §2: relative to the current close."""
    if zone.high < close:
        return ZoneRole.SUPPORT
    if zone.low > close:
        return ZoneRole.RESISTANCE
    return ZoneRole.INSIDE


def distance_pct(zone: Zone, close: Decimal) -> Decimal:
    """TRD-03 §7, in percent; 0 when price is inside the zone."""
    role = zone_role(zone, close)
    if role is ZoneRole.SUPPORT:
        return (close - zone.high) / close * 100
    if role is ZoneRole.RESISTANCE:
        return (zone.low - close) / close * 100
    return Decimal(0)


def nearest(zones: Sequence[Zone], close: Decimal, role: ZoneRole) -> Zone | None:
    """Nearest support or resistance (ties: lower zone first, so the result is deterministic)."""
    cands = [z for z in zones if zone_role(z, close) is role]
    return min(cands, key=lambda z: (distance_pct(z, close), z.low), default=None)


def is_near(zone: Zone, close: Decimal, params: RulesetParams) -> bool:
    return distance_pct(zone, close) <= params.decimal("zone.proximity_pct")
