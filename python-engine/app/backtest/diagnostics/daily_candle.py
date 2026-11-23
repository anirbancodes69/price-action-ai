"""Candle patterns, volume filter and volume audit of the candle and volume screening protocol.

See docs/research/candle-volume-screening-protocol.md. Detectors are pure functions of one series of daily
bars; a signal at session `s` reads only sessions up to and including `s`. The stop range and the
one-position rule are applied by the runner.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.backtest.diagnostics.daily import DayBar
from app.backtest.diagnostics.daily_screen import Signal, stop_below

D = Decimal
STOP_BASE_SESSIONS = 5  # the stop: the lowest low of the signal session and the previous 4
SUPPORT_LOOKBACK = 20
SUPPORT_TOLERANCE = D("1.01")
VOLUME_LOOKBACK = 20
SHIFT_WINDOW = 20
SHIFT_MIN_RATIO = 1.8
SPLIT_RATIOS = (2, 3, 4, 5, 10)
SPLIT_TOLERANCE = 0.08


@dataclass(frozen=True, slots=True)
class CVariant:
    vid: str
    pattern: str  # H hammer, E bullish engulfing, D doji then green
    support: bool  # context S: at the 20-session low
    volume: bool  # filter V: volume at least 1.5x the 20-session mean


FAMILY: tuple[CVariant, ...] = tuple(
    CVariant(f"{pat}-{'S' if sup else 'A'}{'V' if vol else ''}", pat, sup, vol)
    for pat in ("H", "E", "D")
    for sup in (False, True)
    for vol in (False, True)
)


def body(b: DayBar) -> Decimal:
    return abs(b.close - b.open)


def is_hammer(b: DayBar) -> bool:
    """Lower wick at least 60% of the range, body at most 30%, upper wick at most 10% (any colour)."""
    rng = b.high - b.low
    if rng <= 0:
        return False
    lower, upper = min(b.open, b.close) - b.low, b.high - max(b.open, b.close)
    return lower >= D("0.6") * rng and body(b) <= D("0.3") * rng and upper <= D("0.1") * rng


def is_doji(b: DayBar) -> bool:
    rng = b.high - b.low
    return rng > 0 and body(b) <= D("0.1") * rng


def is_bullish_engulfing(prev: DayBar, cur: DayBar) -> bool:
    """A green session whose body covers the previous red body."""
    return (
        prev.close < prev.open and cur.close > cur.open and cur.open <= prev.close and cur.close >= prev.open
    )


def at_support(bars: Sequence[DayBar], i: int) -> bool:
    """Session `i`'s low is at or below 1.01 times the lowest low of the 20 sessions before it."""
    if i < SUPPORT_LOOKBACK:
        return False
    return bars[i].low <= min(b.low for b in bars[i - SUPPORT_LOOKBACK : i]) * SUPPORT_TOLERANCE


def high_volume(bars: Sequence[DayBar], s: int) -> bool:
    """Volume of session `s` at least 1.5 times the mean of the 20 sessions before it (mean above zero)."""
    if s < VOLUME_LOOKBACK:
        return False
    total = sum(b.volume for b in bars[s - VOLUME_LOOKBACK : s])
    return total > 0 and 2 * VOLUME_LOOKBACK * bars[s].volume >= 3 * total


def detect_candle(v: CVariant, bars: Sequence[DayBar], bad_volume: set[int] | None = None) -> list[Signal]:
    """Signals of one variant. With the volume filter, a session whose 20-session volume window is not
    comparable (`bad_volume`, from the volume audit) gives no signal."""
    out: list[Signal] = []
    for s in range(max(1, STOP_BASE_SESSIONS - 1), len(bars)):
        cur, prev = bars[s], bars[s - 1]
        if v.pattern == "H":
            ok, ctx = is_hammer(cur), s
        elif v.pattern == "E":
            ok, ctx = is_bullish_engulfing(prev, cur), s
        else:
            ok, ctx = is_doji(prev) and cur.close > cur.open and cur.close > prev.high, s - 1
        if not ok or (v.support and not at_support(bars, ctx)):
            continue
        if v.volume and ((bad_volume is not None and s in bad_volume) or not high_volume(bars, s)):
            continue
        low = min(b.low for b in bars[s - STOP_BASE_SESSIONS + 1 : s + 1])
        out.append(Signal(s, cur.close, stop_below(low)))
    return out


def volume_level_shifts(volumes: Sequence[int]) -> list[tuple[int, float, bool]]:
    """Level shifts of volume: `(index, ratio, split_like)` where the median of the 20 sessions from `index`
    over the median of the 20 before it is at least 1.8 times or at most 1/1.8. Among neighbouring candidates
    the index with the largest change of the 20-session *mean* is kept (exact for a step). `split_like` when
    the ratio is within 8% of 2, 3, 4, 5, 10 or their inverses (an unadjusted split or bonus leaves it)."""
    n = len(volumes)
    med: dict[int, float] = {}
    mean: dict[int, float] = {}
    for d in range(SHIFT_WINDOW, n - SHIFT_WINDOW + 1):
        before, after = volumes[d - SHIFT_WINDOW : d], volumes[d : d + SHIFT_WINDOW]
        mb, ma = statistics.median(before), statistics.median(after)
        if mb > 0 and ma > 0 and sum(before) > 0 and sum(after) > 0:
            med[d] = ma / mb
            mean[d] = sum(after) / sum(before)
    big = [d for d, r in med.items() if abs(math.log(r)) >= math.log(SHIFT_MIN_RATIO)]
    out = []
    for d in big:
        near = [x for x in big if abs(x - d) <= SHIFT_WINDOW]
        best = max(abs(math.log(mean[x])) for x in near)
        first = min(x for x in near if abs(math.log(mean[x])) == best)
        if d != first:
            continue
        r = med[d]
        split = any(
            abs(r / k - 1) <= SPLIT_TOLERANCE or abs(r * k - 1) <= SPLIT_TOLERANCE for k in SPLIT_RATIOS
        )
        out.append((d, r, split))
    return out


def non_comparable_sessions(shifts: Sequence[tuple[int, float, bool]]) -> set[int]:
    """Sessions whose 20-session volume window straddles a split-like level shift: `[index, index + 20]`."""
    bad: set[int] = set()
    for d, _, split in shifts:
        if split:
            bad.update(range(d, d + SHIFT_WINDOW + 1))
    return bad
