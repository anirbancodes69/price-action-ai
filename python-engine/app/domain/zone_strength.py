"""Zone touches and strength score (TRD-03 §4)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.types import Bar, PivotKind
from app.domain.zones import StrengthBucket, ZoneMember

# TRD-03 §4.2 constants (HYPOTHESIS, not in the TRD-01 registry yet).
TOUCH_PTS, MAX_TOUCHES = 15, 4
REACTION_PTS_PER_PCT, MAX_REACTION_PCT = Decimal(10), Decimal(2)
REACTION_BARS = 6
RECENT_CURRENT_PTS, RECENT_PREVIOUS_PTS = 20, 10
HTF_PTS, FLIP_PTS = 5, 10
MODERATE_FROM, STRONG_FROM = 40, 70


@dataclass(frozen=True, slots=True)
class TouchStats:
    touches: int
    max_reaction_pct: Decimal
    last_touch_start: datetime | None


def _reaction_pct(
    bars: Sequence[Bar], after: int, t: int, low: Decimal, high: Decimal, away_up: bool
) -> Decimal:
    window = bars[after + 1 : min(after + REACTION_BARS, t) + 1]
    if not window:
        return Decimal(0)
    mid = (low + high) / 2
    move = max(b.high for b in window) - high if away_up else low - min(b.low for b in window)
    return max(move, Decimal(0)) / mid * 100


def touch_stats(
    bars: Sequence[Bar],
    members: Sequence[ZoneMember],
    low: Decimal,
    high: Decimal,
    formed_at_index: int,
    t: int,
    reaction_window: int,
) -> TouchStats:
    """Touches = member pivots + confirmed later touches (TRD-03 §4.1).

    A later touch is a run of consecutive bars whose range intersects the zone, followed within
    `reaction_window` bars (up to `t`) by a close outside the zone on the side price came from.
    """
    count = len(members)
    best = Decimal(0)
    last: datetime | None = max(m.pivot.bar_start for m in members) if members else None
    for m in members:
        away_up = m.pivot.kind is PivotKind.LOW  # a low pivot is support: price moved up after it
        best = max(best, _reaction_pct(bars, m.bar_index_5m, t, low, high, away_up))

    j = formed_at_index + 1
    while j <= t:
        if not (bars[j].low <= high and bars[j].high >= low):
            j += 1
            continue
        g0 = j
        while j + 1 <= t and bars[j + 1].low <= high and bars[j + 1].high >= low:
            j += 1
        g1 = j
        j += 1
        prev_close = bars[g0 - 1].close
        if prev_close > high:
            from_above = True
        elif prev_close < low:
            from_above = False
        else:
            continue  # came from inside the zone: side unknown
        react = bars[g1 + 1 : min(g1 + reaction_window, t) + 1]
        if any((b.close > high) if from_above else (b.close < low) for b in react):
            count += 1
            best = max(best, _reaction_pct(bars, g1, t, low, high, away_up=from_above))
            if last is None or bars[g1].start > last:
                last = bars[g1].start
    return TouchStats(count, best, last)


def strength_score(
    stats: TouchStats,
    current_session_open: datetime,
    previous_session_open: datetime | None,
    has_htf_member: bool,
    role_reversed: bool,
) -> tuple[int, StrengthBucket]:
    touch_pts = min(stats.touches, MAX_TOUCHES) * TOUCH_PTS
    reaction_pts = int(min(stats.max_reaction_pct, MAX_REACTION_PCT) * REACTION_PTS_PER_PCT)
    recency = 0
    if stats.last_touch_start is not None:
        if stats.last_touch_start >= current_session_open:
            recency = RECENT_CURRENT_PTS
        elif previous_session_open is not None and stats.last_touch_start >= previous_session_open:
            recency = RECENT_PREVIOUS_PTS
    total = touch_pts + reaction_pts + recency + (HTF_PTS if has_htf_member else 0)
    total += FLIP_PTS if role_reversed else 0
    score = min(100, total)
    bucket = (
        StrengthBucket.STRONG
        if score >= STRONG_FROM
        else StrengthBucket.MODERATE
        if score >= MODERATE_FROM
        else StrengthBucket.WEAK
    )
    return score, bucket
