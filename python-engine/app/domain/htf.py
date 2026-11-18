"""Higher-timeframe alignment without look-ahead (TRD-02 §9, TRD-01 MP-10)."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.domain.types import Bar, BarState, StructureResult


@dataclass(frozen=True, slots=True)
class HtfContext:
    """15m context visible to a 5m bar. `index`/`state` are None before the first 15m bar closed."""

    index: int | None
    state: BarState | None


def align_htf(
    ends_5m: Sequence[datetime],
    bars_htf: Sequence[Bar],
    htf: StructureResult,
) -> list[HtfContext]:
    """For each 5m bar end `E`: the largest 15m index `j` with `end_15m[j] <= E`.

    A 15m bar that has not closed by `E` is ignored, never rebuilt from 5m bars.
    `htf` must be `run_structure` output over `bars_htf` (one state per bar).
    """
    ends = [b.end for b in bars_htf]
    out: list[HtfContext] = []
    for e in ends_5m:
        j = bisect_right(ends, e) - 1
        out.append(HtfContext(None, None) if j < 0 else HtfContext(j, htf.states[j]))
    return out
