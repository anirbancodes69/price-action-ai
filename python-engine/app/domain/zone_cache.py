"""Memo of `build_zones` results across the analyses of one replay (a pure speed-up, never a rule).

`build_zones(..., t, ...)` reads only bars up to `t` and pivots confirmed by `t`, so for a growing bar series
its result at index `t` is the same in every later analysis. The setup detector asks for the zones at every
bar of the session on every analysis; this cache lets the backtest compute each one once. The cache is
opt-in: without one, `build_zones` is called exactly as before, and results are identical either way
(`tests/backtest/test_zone_cache.py`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from app.domain.params import RulesetParams
from app.domain.types import Bar, SwingPoint
from app.domain.zone_build import build_zones
from app.domain.zones import Zone


class ZoneCache:
    """Zones by bar index for one symbol's growing bar series; keyed so that a different input never hits."""

    def __init__(self) -> None:
        self._zones: dict[tuple[object, ...], list[Zone]] = {}

    def zones(
        self,
        bars_5m: Sequence[Bar],
        pivots_5m: Sequence[SwingPoint],
        pivots_15m: Sequence[SwingPoint],
        t: int,
        params: RulesetParams,
        current_session_open: datetime,
        previous_session_open: datetime | None,
        tick: Decimal | None,
    ) -> list[Zone]:
        key = (
            t,
            bars_5m[0].start,
            bars_5m[t].start,
            bars_5m[t].close,
            current_session_open,
            previous_session_open,
            tick,
            params.code,
            params.version,
        )
        hit = self._zones.get(key)
        if hit is None:
            hit = build_zones(
                bars_5m, pivots_5m, pivots_15m, t, params, current_session_open, previous_session_open, tick
            )
            self._zones[key] = hit
        return list(hit)  # a copy: callers may not alter the cached list
