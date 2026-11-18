"""Build one instrument's analysis input from stored candles, as of a moment in time (TRD-01 §4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import Connection, func, select

from app.backtest.loader import load_bars, previous_day_levels, session_spec, tick_and_lot
from app.backtest.replay import SessionSpec, SymbolData
from app.db.tables import candles
from app.ingestion.session import IST


def latest_bar_end(
    conn: Connection, source: uuid.UUID, instrument_id: uuid.UUID, as_of: datetime | None = None
) -> datetime | None:
    """End of the latest stored 5m bar (at or before `as_of`), or `None` when there is none."""
    q = select(func.max(candles.c.bar_start)).where(
        candles.c.data_source_id == source,
        candles.c.instrument_id == instrument_id,
        candles.c.timeframe == "5m",
    )
    if as_of is not None:
        q = q.where(candles.c.bar_start <= as_of - timedelta(minutes=5))
    start = conn.execute(q).scalar()
    return None if start is None else start + timedelta(minutes=5)


def load_symbol_snapshot(
    conn: Connection,
    source: uuid.UUID,
    instrument_id: uuid.UUID,
    symbol: str,
    lookback_sessions: int,
    as_of: datetime | None = None,
) -> tuple[SymbolData, SessionSpec] | None:
    """Closed bars of the latest session at/before `as_of` plus `lookback_sessions` earlier ones.

    Only bars that ended at or before `as_of` are used (BT-01). Previous-day levels come from the previous
    session's stored 5m bars. Returns `None` when the instrument has no stored bars.
    """
    end = latest_bar_end(conn, source, instrument_id, as_of)
    if end is None:
        return None
    day: date = (end - timedelta(seconds=1)).astimezone(IST).date()
    margin = timedelta(days=lookback_sessions * 2 + 7)
    five = load_bars(conn, source, instrument_id, "5m", day - margin, day)
    five = [b for b in five if b.end <= end]
    days = sorted({b.start.astimezone(IST).date() for b in five})
    window = days[-(lookback_sessions + 1) :]
    five = [b for b in five if b.start.astimezone(IST).date() in set(window)]
    previous = days[-2] if len(days) >= 2 else None
    prev_bars = [b for b in five if previous and b.start.astimezone(IST).date() == previous]
    fifteen = [b for b in load_bars(conn, source, instrument_id, "15m", window[0], day) if b.end <= end]
    tick, lot = tick_and_lot(conn, instrument_id, day)
    spec = session_spec(conn, day, previous)
    return SymbolData(symbol, five, fifteen, previous_day_levels(prev_bars), tick, lot), spec
