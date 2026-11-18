"""Equal highs / equal lows liquidity pools (TRD-03 §6)."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.types import Bar, PivotKind, SwingPoint

MIN_BAR_GAP = 3  # TRD-03 §6: b.index - a.index >= 3 five-minute bars


class PoolType(StrEnum):
    EQUAL_HIGHS = "EQUAL_HIGHS"
    EQUAL_LOWS = "EQUAL_LOWS"


@dataclass(frozen=True, slots=True)
class LiquidityPool:
    type: PoolType
    level: Decimal  # max for highs, min for lows
    first_index: int
    second_index: int
    confirmed_at_index: int


def equal_levels(
    bars_5m: Sequence[Bar],
    pivots_5m: Sequence[SwingPoint],
    t: int,
    equal_tolerance: Decimal,
) -> list[LiquidityPool]:
    """Pools from consecutive same-kind 5m pivots confirmed by `t` (TRD-03 §6).

    Equal when within `equal_tolerance` of the earlier pivot, at least 3 bars apart, and no close between
    the two pivots went beyond the pool level.
    """
    pools: list[LiquidityPool] = []
    for kind, ptype in ((PivotKind.HIGH, PoolType.EQUAL_HIGHS), (PivotKind.LOW, PoolType.EQUAL_LOWS)):
        seq = [p for p in pivots_5m if p.kind is kind and p.confirmed_at_index <= t]
        for a, b in itertools.pairwise(seq):
            if abs(b.price - a.price) / a.price > equal_tolerance or b.index - a.index < MIN_BAR_GAP:
                continue
            closes = [bars_5m[i].close for i in range(a.index, b.index + 1)]
            if kind is PivotKind.HIGH:
                level = max(a.price, b.price)
                broken = any(c > level for c in closes)
            else:
                level = min(a.price, b.price)
                broken = any(c < level for c in closes)
            if not broken:
                pools.append(LiquidityPool(ptype, level, a.index, b.index, b.confirmed_at_index))
    return pools
