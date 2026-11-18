"""NSE regular-session bar grid (IST). Normal session 09:15-15:30: 75 5m and 25 15m bars (ENG-05 §12).

Special sessions and holidays come from ``market_calendar``, not from this module.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.providers.base import Timeframe

IST = ZoneInfo("Asia/Kolkata")
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)
_MINUTES: dict[str, int] = {"5m": 5, "15m": 15}


def bar_minutes(timeframe: Timeframe) -> int:
    if timeframe not in _MINUTES:
        raise ValueError(f"no intraday grid for {timeframe}")
    return _MINUTES[timeframe]


def session_bounds(day: date, close: time | None = None) -> tuple[datetime, datetime]:
    """Session open and close in IST. ``close`` overrides the end (a provider's intraday cutoff)."""
    end = min(SESSION_CLOSE, close) if close is not None else SESSION_CLOSE
    return datetime.combine(day, SESSION_OPEN, IST), datetime.combine(day, end, IST)


def session_bar_starts(day: date, timeframe: Timeframe, close: time | None = None) -> list[datetime]:
    """Every expected ``bar_start`` of a normal session, ending at ``close`` if given."""
    step = timedelta(minutes=bar_minutes(timeframe))
    cur, close_at = session_bounds(day, close)
    out: list[datetime] = []
    while cur + step <= close_at:
        out.append(cur)
        cur += step
    return out
