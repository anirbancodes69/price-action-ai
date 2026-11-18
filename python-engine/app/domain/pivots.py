"""Swing pivots and labels (TRD-02 §3, §4)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal

from app.domain.types import Bar, PivotKind, SwingLabel, SwingPoint


def detect_pivots(bars: Sequence[Bar], left: int, right: int) -> list[SwingPoint]:
    """TRD-02 §3.1-§3.4. Unlabelled pivots in confirmation order.

    A pivot at `i` needs `i >= left` and `i + right <= len(bars) - 1`, so a
    truncated series never contains a pivot that was not yet confirmed.
    """
    n = len(bars)
    found: list[SwingPoint] = []
    for i in range(left, n - right):
        b = bars[i]
        is_high = all(b.high > bars[i - k].high for k in range(1, left + 1)) and all(
            b.high >= bars[i + k].high for k in range(1, right + 1)
        )
        is_low = all(b.low < bars[i - k].low for k in range(1, left + 1)) and all(
            b.low <= bars[i + k].low for k in range(1, right + 1)
        )
        conf = bars[i + right]
        high = SwingPoint(PivotKind.HIGH, i, b.high, b.start, i + right, conf.end)
        low = SwingPoint(PivotKind.LOW, i, b.low, b.start, i + right, conf.end)
        # §3.3: outside bar -> low first if bullish (close >= open), else high first.
        if is_high and is_low:
            found.extend([low, high] if b.close >= b.open else [high, low])
        elif is_high:
            found.append(high)
        elif is_low:
            found.append(low)
    return found


def label_pivots(pivots: Sequence[SwingPoint], equal_tolerance: Decimal) -> list[SwingPoint]:
    """TRD-02 §4: label against the previous same-kind pivot; never revised.

    `pivots` must be in confirmation order, as `detect_pivots` returns them.
    """
    prev: dict[PivotKind, Decimal] = {}
    out: list[SwingPoint] = []
    for p in pivots:
        ref = prev.get(p.kind)
        if ref is None:
            label = SwingLabel.NONE
        else:
            up, down = ref * (1 + equal_tolerance), ref * (1 - equal_tolerance)
            if p.kind is PivotKind.HIGH:
                label = SwingLabel.HH if p.price > up else SwingLabel.LH if p.price < down else SwingLabel.EQH
            else:
                label = SwingLabel.HL if p.price > up else SwingLabel.LL if p.price < down else SwingLabel.EQL
        prev[p.kind] = p.price
        out.append(replace(p, label=label))
    return out
