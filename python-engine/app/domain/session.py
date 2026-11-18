"""Session conventions and reference levels (TRD-01 §4.1, TRD-03 §8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.types import Bar


@dataclass(frozen=True, slots=True)
class DailyLevels:
    """High, low, close of the previous completed session's daily bar."""

    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class SessionLevels:
    """TRD-03 §8. `None` means the level does not exist yet (or context is missing)."""

    pdh: Decimal | None
    pdl: Decimal | None
    pdc: Decimal | None
    or_high: Decimal | None
    or_low: Decimal | None
    session_high: Decimal | None
    session_low: Decimal | None


def entry_cutoff(session_close: datetime, minutes_before_close: int) -> datetime:
    """TRD-01 §4.1: no setup reaches ENTRY_CONFIRMED and no plan is created at or after this time."""
    return session_close - timedelta(minutes=minutes_before_close)


def session_exit_time(session_close: datetime, minutes_before_close: int) -> datetime:
    """TRD-01 §4.1: open paper positions are exited at this time (SESSION_END)."""
    return session_close - timedelta(minutes=minutes_before_close)


def session_levels(
    bars_5m: Sequence[Bar],
    session_open: datetime,
    prev_day: DailyLevels | None,
    opening_range_minutes: int,
) -> SessionLevels:
    """Reference levels at the latest closed 5m bar of the session.

    `bars_5m` are closed bars; bars starting before `session_open` are ignored. The opening range
    exists only once a bar ending at or after `session_open + opening_range_minutes` has closed.
    """
    today = [b for b in bars_5m if b.start >= session_open]
    or_end = session_open + timedelta(minutes=opening_range_minutes)
    or_bars = [b for b in today if b.end <= or_end]
    or_known = any(b.end >= or_end for b in today)
    return SessionLevels(
        pdh=prev_day.high if prev_day else None,
        pdl=prev_day.low if prev_day else None,
        pdc=prev_day.close if prev_day else None,
        or_high=max(b.high for b in or_bars) if or_known and or_bars else None,
        or_low=min(b.low for b in or_bars) if or_known and or_bars else None,
        session_high=max(b.high for b in today) if today else None,
        session_low=min(b.low for b in today) if today else None,
    )
