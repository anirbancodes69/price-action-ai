"""The four daily entry ideas and the family of the daily screening protocol.

Detectors are pure functions of one series of daily bars (chronological). A signal at session `s` reads only
sessions up to and including `s` (closed bars; pivots only from their confirmation session), so a later bar
never changes it. The stop range and the one-position rule are applied by the runner, not here.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from app.backtest.diagnostics.daily import DayBar

D = Decimal
TICK = D("0.05")
BUFFER_PCT = D("0.05")  # below the stop level, as `risk.stop_buffer_pct`; also the breakdown buffer
STOP_MIN_PCT = D(4)
STOP_MAX_PCT = D(10)
HOLD = 20
PIVOT = 2  # sessions on each side (the ruleset's pivot parameters)
RECLAIM_SESSIONS = 3
STOP_BASE_SESSIONS = 20  # the breakout's stop: the lowest low of the last 20 sessions


@dataclass(frozen=True, slots=True)
class Signal:
    index: int  # signal session; its close is the reference entry
    ref: Decimal
    stop: Decimal

    @property
    def stop_pct(self) -> Decimal:
        return (self.ref - self.stop) / self.ref * 100


@dataclass(frozen=True, slots=True)
class Variant:
    vid: str
    idea: str  # P1, B2, F3 or C4
    param: Decimal  # P1: depth %; B2, F3: sessions; C4: fall %


FAMILY: tuple[Variant, ...] = (
    Variant("P1a", "P1", D(3)),
    Variant("P1b", "P1", D(6)),
    Variant("B2a", "B2", D(50)),
    Variant("B2b", "B2", D(100)),
    Variant("F3a", "F3", D(20)),
    Variant("F3b", "F3", D(50)),
    Variant("C4a", "C4", D(4)),
    Variant("C4b", "C4", D(6)),
)


def floor_tick(x: Decimal, tick: Decimal = TICK) -> Decimal:
    return (x / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def stop_below(level: Decimal) -> Decimal:
    return floor_tick(level * (1 - BUFFER_PCT / 100))


def pivots(bars: Sequence[DayBar], left: int = PIVOT, right: int = PIVOT) -> tuple[list[int], list[int]]:
    """Swing pivot indices `(highs, lows)`, by the intraday rule (TRD-02 §3): a high is strictly above
    the `left` sessions before it and at least as high as the `right` after it; a low mirrors that.
    A session that is both is listed in both. A pivot at `i` is confirmed at `i + right`."""
    highs: list[int] = []
    lows: list[int] = []
    for i in range(left, len(bars) - right):
        b = bars[i]
        if all(b.high > bars[i - k].high for k in range(1, left + 1)) and all(
            b.high >= bars[i + k].high for k in range(1, right + 1)
        ):
            highs.append(i)
        if all(b.low < bars[i - k].low for k in range(1, left + 1)) and all(
            b.low <= bars[i + k].low for k in range(1, right + 1)
        ):
            lows.append(i)
    return highs, lows


def detect_p1(bars: Sequence[DayBar], depth_pct: Decimal) -> list[Signal]:
    """Trend pullback. At session `s` (pivots confirmed by `s`): the last two swing highs rise, the
    last two swing lows rise, the latest swing low is before the latest swing high, the pullback low
    (lowest low after that swing high, up to `s - 1`) is at least `depth_pct` below the swing high
    and above the latest swing low. The signal is the first such session with a close above the
    previous session's high; one per swing high. The stop is below the pullback low."""
    highs, lows = pivots(bars)
    out: list[Signal] = []
    used: set[int] = set()
    for s in range(1, len(bars)):
        nh = bisect.bisect_right(highs, s - PIVOT)  # pivots confirmed by s
        nl = bisect.bisect_right(lows, s - PIVOT)
        if nh < 2 or nl < 2:
            continue
        h1, h2, l1, l2 = highs[nh - 2], highs[nh - 1], lows[nl - 2], lows[nl - 1]
        if bars[h2].high <= bars[h1].high or bars[l2].low <= bars[l1].low or l2 >= h2 or h2 in used:
            continue
        window = range(h2 + 1, s)
        if not window:
            continue
        m = min(window, key=lambda j: bars[j].low)  # the first lowest low
        low = bars[m].low
        if low <= bars[l2].low or (bars[h2].high - low) / bars[h2].high * 100 < depth_pct:
            continue
        if bars[s].close > bars[s - 1].high:
            used.add(h2)
            out.append(Signal(s, bars[s].close, stop_below(low)))
    return out


def detect_b2(bars: Sequence[DayBar], n: int) -> list[Signal]:
    """Breakout of a long range: the first session whose close is above the highest high of the
    previous `n` sessions (the session before was not itself such a breakout). The stop is below the
    lowest low of the last 20 sessions, including the signal session."""
    out: list[Signal] = []

    def above(s: int) -> bool:
        return s >= n and bars[s].close > max(b.high for b in bars[s - n : s])

    for s in range(n, len(bars)):
        if above(s) and not above(s - 1):
            low = min(b.low for b in bars[max(0, s - STOP_BASE_SESSIONS + 1) : s + 1])
            out.append(Signal(s, bars[s].close, stop_below(low)))
    return out


def detect_f3(bars: Sequence[DayBar], n: int) -> list[Signal]:
    """Failed breakdown at support. Level Y is the lowest low of the previous `n` sessions. A breakdown
    is the first of consecutive sessions closing below `Y * (1 - 0.05%)`; the signal is the first
    session within 3 after it closing at or above Y (Y as at the breakdown). The stop is below the
    lowest low from the breakdown to the signal session. A breakdown without a reclaim gives no
    signal."""
    out: list[Signal] = []

    def broken(s: int) -> bool:
        return s >= n and bars[s].close < min(b.low for b in bars[s - n : s]) * (1 - BUFFER_PCT / 100)

    for b in range(n, len(bars)):
        if not broken(b) or broken(b - 1):
            continue
        level = min(x.low for x in bars[b - n : b])
        for r in range(b + 1, min(b + RECLAIM_SESSIONS, len(bars) - 1) + 1):
            if bars[r].close >= level:
                out.append(Signal(r, bars[r].close, stop_below(min(x.low for x in bars[b : r + 1]))))
                break
    return out


def detect_c4(bars: Sequence[DayBar], fall_pct: Decimal) -> list[Signal]:
    """Selling climax: a close at least `fall_pct` below the previous close and in the top third of the
    session's own range. The stop is below the session's low."""
    out: list[Signal] = []
    for s in range(1, len(bars)):
        b, prev = bars[s], bars[s - 1]
        falls = (prev.close - b.close) / prev.close * 100 >= fall_pct
        if b.high > b.low and falls and 3 * (b.close - b.low) >= 2 * (b.high - b.low):
            out.append(Signal(s, b.close, stop_below(b.low)))
    return out


def detect(v: Variant, bars: Sequence[DayBar]) -> list[Signal]:
    if v.idea == "P1":
        return detect_p1(bars, v.param)
    if v.idea == "B2":
        return detect_b2(bars, int(v.param))
    if v.idea == "F3":
        return detect_f3(bars, int(v.param))
    if v.idea == "C4":
        return detect_c4(bars, v.param)
    raise ValueError(f"unknown idea {v.idea}")


def passes_stop_range(sig: Signal) -> bool:
    return STOP_MIN_PCT <= sig.stop_pct <= STOP_MAX_PCT
