"""Strict opening-range data validation, `ORB-MG-02` (ORB specification §7.1.2; E3, OD-8 step 1).

A pure function of the stored 5m bars: no I/O, no clock, no tolerance. It implements the **frozen** text
of `ORB-MG-02`. It is not wired into any detector yet: today's `detect_opening_range` and `session_levels`
still form the range from whatever bars exist (the defect of §17.1 item 1). The B0 path (E4, not yet
authorised) will call it.

What it does not do, on purpose:
- It does not read or assume a tick size. The tick check of the frozen text ("each price is a multiple of
  the tick when the tick is known") runs only when the caller passes `tick`. There is no default:
  `tick=None` means "not checked" and the result says so (`tick_checked = False`). Stored candles are
  provider-adjusted for part of the history, so a caller must pass a tick only for a session whose price scale
  is verified as traded and whose tick is resolved from the historical rules. The amendment MG02-A1 (four
  tick statuses) is **not adopted** and is not implemented here.
- It does not decide which sessions are special (`ORB-MG-01`); the caller passes `session_excluded`.
- It does not use volume (not a validity input).

Interpretation points the specification leaves open (each is documented here and in the E3 report):
- Precedence of the reported reason when several checks fail: the order of the specification's table
  (count, grid, closed, valid OHLC, session). `reasons` always lists every failing check in that order.
- An off-grid start time inside the window counts as a missing grid slot (`OR_MISSING_BAR`); a repeated start
  time counts as `OR_DUPLICATE_BAR`.
- A series that has not yet reached `t_OR` (no bar ends at or after it) is `OR_NOT_CLOSED` and no other check
  is reported, because the count of a half-formed range says nothing about the data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from app.domain.types import Bar

BAR_MINUTES = 5


class OrbRangeReason(StrEnum):
    """Sub-reasons of `ORB-MG-02` (§7.1.2) and the session gate of `ORB-MG-01`."""

    OR_MISSING_BAR = "OR_MISSING_BAR"
    OR_DUPLICATE_BAR = "OR_DUPLICATE_BAR"
    OR_NOT_CLOSED = "OR_NOT_CLOSED"
    OR_INVALID_OHLC = "OR_INVALID_OHLC"
    SESSION_EXCLUDED = "SESSION_EXCLUDED"


@dataclass(frozen=True, slots=True)
class OrbRange:
    valid: bool
    reason: OrbRangeReason | None  # the first failing check in the specification's table order
    reasons: tuple[OrbRangeReason, ...]  # every failing check, in that order
    or_high: Decimal | None  # max high of the K bars (wick basis); None unless valid
    or_low: Decimal | None  # min low of the K bars (wick basis); None unless valid
    t_or: datetime  # E(K-1): the end of the last range bar
    bars_in_window: int
    tick_checked: bool  # False when no tick was supplied (never a default)


def _is_multiple(price: Decimal, tick: Decimal) -> bool:
    return price % tick == 0


def _ohlc_ok(b: Bar, tick: Decimal | None) -> bool:
    prices = (b.open, b.high, b.low, b.close)
    if not all(p.is_finite() and p > 0 for p in prices):
        return False
    if b.high < max(b.open, b.close) or b.low > min(b.open, b.close) or b.high < b.low:
        return False
    return tick is None or all(_is_multiple(p, tick) for p in prices)


def validate_opening_range(
    bars: Sequence[Bar],
    session_open: datetime,
    opening_range_minutes: int = 15,
    *,
    session_excluded: bool = False,
    tick: Decimal | None = None,
) -> OrbRange:
    """Validate the opening range of one instrument-session at `t_OR = session_open + opening_range_minutes`.

    `bars` are the stored closed 5m bars of the session (any order; the input is not modified).
    `opening_range_minutes` must be a positive multiple of 5 (`K = N / 5` bars).
    """
    if opening_range_minutes <= 0 or opening_range_minutes % BAR_MINUTES:
        raise ValueError("opening_range_minutes must be a positive multiple of 5")
    if tick is not None and (not tick.is_finite() or tick <= 0):
        raise ValueError("tick must be a positive finite Decimal or None")
    k = opening_range_minutes // BAR_MINUTES
    t_or = session_open + timedelta(minutes=opening_range_minutes)
    ordered = sorted(bars, key=lambda b: (b.start, b.end))

    def result(reasons: list[OrbRangeReason], window: list[Bar]) -> OrbRange:
        valid = not reasons
        return OrbRange(
            valid,
            reasons[0] if reasons else None,
            tuple(reasons),
            max(b.high for b in window) if valid else None,
            min(b.low for b in window) if valid else None,
            t_or,
            len(window),
            tick is not None,
        )

    window = [b for b in ordered if session_open <= b.start < t_or]
    # Closed: the series must reach t_OR. Otherwise the range is not formed yet and nothing else is judged.
    if not any(b.end >= t_or for b in ordered):
        return result([OrbRangeReason.OR_NOT_CLOSED], window)

    reasons: list[OrbRangeReason] = []
    starts = [b.start for b in window]
    expected = {session_open + timedelta(minutes=BAR_MINUTES * i) for i in range(k)}
    # Count and grid (rows 1-2 of the table): exactly K bars, at exactly session_open + 5i, none repeated.
    if len(starts) > k or len(set(starts)) < len(starts):
        reasons.append(OrbRangeReason.OR_DUPLICATE_BAR)
    if expected - set(starts):
        reasons.append(OrbRangeReason.OR_MISSING_BAR)
    # Closed (row 3): every bar of the window ends at or before t_OR and is exactly one bar long.
    if any(b.end > t_or or b.end - b.start != timedelta(minutes=BAR_MINUTES) for b in window):
        reasons.append(OrbRangeReason.OR_NOT_CLOSED)
    # Valid OHLC (row 4), including the tick multiple only when a tick is supplied.
    if any(not _ohlc_ok(b, tick) for b in window):
        reasons.append(OrbRangeReason.OR_INVALID_OHLC)
    # Session (row 5, ORB-MG-01).
    if session_excluded:
        reasons.append(OrbRangeReason.SESSION_EXCLUDED)
    # Primary reason in the specification's table order: count/grid, closed, valid OHLC, session.
    table_order = [
        OrbRangeReason.OR_MISSING_BAR,
        OrbRangeReason.OR_DUPLICATE_BAR,
        OrbRangeReason.OR_NOT_CLOSED,
        OrbRangeReason.OR_INVALID_OHLC,
        OrbRangeReason.SESSION_EXCLUDED,
    ]
    reasons = sorted(reasons, key=table_order.index)
    return result(reasons, window)
