"""Zone types and pivot clustering (TRD-03 §3)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import StrEnum

from app.domain.types import Direction, SwingPoint, Timeframe


class ZoneStatus(StrEnum):
    """TRD-03 §5.3."""

    ACTIVE = "ACTIVE"
    BROKEN_FLIPPED = "BROKEN_FLIPPED"
    RETIRED = "RETIRED"


class ZoneRole(StrEnum):
    """Relative to the current close (TRD-03 §2, §7)."""

    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"
    INSIDE = "INSIDE"


class StrengthBucket(StrEnum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


@dataclass(frozen=True, slots=True)
class ZoneMember:
    """A confirmed pivot used for a zone, with its position on the 5m series."""

    timeframe: Timeframe
    pivot: SwingPoint
    bar_index_5m: int  # 5m bar holding (or starting at) the pivot bar
    known_index_5m: int  # first 5m bar whose close is at/after the pivot's confirmation


@dataclass(frozen=True, slots=True)
class Zone:
    low: Decimal
    high: Decimal
    members: tuple[ZoneMember, ...]
    formed_at_index: int
    status: ZoneStatus = ZoneStatus.ACTIVE
    broken_direction: Direction | None = None
    broken_at_index: int | None = None
    retired_at_index: int | None = None
    touches: int = 0
    strength: int = 0
    bucket: StrengthBucket = StrengthBucket.WEAK

    @property
    def role_reversed(self) -> bool:
        return self.status is not ZoneStatus.ACTIVE

    @property
    def has_htf_member(self) -> bool:
        return any(m.timeframe == "15m" for m in self.members)


@dataclass(frozen=True, slots=True)
class Cluster:
    low: Decimal
    high: Decimal
    members: tuple[ZoneMember, ...]


def _sort_key(m: ZoneMember) -> tuple[Decimal, int, str, str]:
    return (m.pivot.price, m.pivot.index, m.timeframe, m.pivot.kind.value)


def _round_to_tick(low: Decimal, high: Decimal, tick: Decimal) -> tuple[Decimal, Decimal]:
    """Round bounds outward to the tick and make the zone at least 2 ticks wide (TRD-03 §10)."""
    lo = (low / tick).to_integral_value(ROUND_FLOOR) * tick
    hi = (high / tick).to_integral_value(ROUND_CEILING) * tick
    deficit = 2 - int((hi - lo) / tick)
    if deficit > 0:
        lo -= tick * ((deficit + 1) // 2)
        hi += tick * (deficit // 2)
    return lo, hi


def cluster_pivots(
    members: Sequence[ZoneMember],
    tolerance: Decimal,
    min_width: Decimal,
    tick: Decimal | None = None,
) -> list[Cluster]:
    """Deterministic greedy clustering anchored at the cluster's lowest price (TRD-03 §3).

    `tolerance` and `min_width` are fractions. A cluster narrower than `min_width` (relative to its low)
    is widened symmetrically around its midpoint to exactly `min_width` of the midpoint. Overlapping
    zones are merged (TRD-03 §10).
    """
    raw: list[list[ZoneMember]] = []
    for m in sorted(members, key=_sort_key):
        if raw and m.pivot.price <= min(x.pivot.price for x in raw[-1]) * (1 + tolerance):
            raw[-1].append(m)
        else:
            raw.append([m])

    spans: list[tuple[Decimal, Decimal, list[ZoneMember]]] = []
    for group in raw:
        lo = min(x.pivot.price for x in group)
        hi = max(x.pivot.price for x in group)
        if (hi - lo) / lo < min_width:
            mid = (lo + hi) / 2
            half = mid * min_width / 2
            lo, hi = mid - half, mid + half
        if tick is not None:
            lo, hi = _round_to_tick(lo, hi, tick)
        spans.append((lo, hi, group))

    merged: list[tuple[Decimal, Decimal, list[ZoneMember]]] = []
    for lo, hi, group in sorted(spans, key=lambda s: (s[0], s[1])):
        if merged and lo <= merged[-1][1]:
            plo, phi, pg = merged[-1]
            merged[-1] = (min(plo, lo), max(phi, hi), [*pg, *group])
        else:
            merged.append((lo, hi, group))
    return [Cluster(lo, hi, tuple(sorted(g, key=_sort_key))) for lo, hi, g in merged]
