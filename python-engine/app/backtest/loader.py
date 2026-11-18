"""Load stored candles into backtest inputs (TRD-06 §3).

Sessions come from the days that have 5m bars (NSE holidays are not loaded, so the calendar cannot be
trusted yet); a `market_calendar` row, when present, overrides the normal 09:15-15:30 hours. Previous-day
levels are derived from the previous session's stored 5m bars. With Kite that means PDH/PDL/PDC exclude the
last 15 minutes of the session (bars end at 15:15), so they can differ slightly from the official daily bar.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import Connection, select

from app.backtest.replay import SessionSpec, SymbolData
from app.backtest.run import SessionInput
from app.db.tables import candles, instrument_snapshots
from app.domain.session import DailyLevels
from app.domain.types import Bar
from app.ingestion.schedule import trading_session
from app.ingestion.session import IST

NORMAL_OPEN, NORMAL_CLOSE = time(9, 15), time(15, 30)
STEP = {"5m": timedelta(minutes=5), "15m": timedelta(minutes=15)}


def load_bars(
    conn: Connection, source: uuid.UUID, instrument_id: uuid.UUID, timeframe: str, first: date, last: date
) -> list[Bar]:
    """Closed bars of one instrument and timeframe with `trade_date` in `first..last`, chronological."""
    rows = conn.execute(
        select(candles.c.bar_start, candles.c.open, candles.c.high, candles.c.low, candles.c.close)
        .where(
            candles.c.data_source_id == source,
            candles.c.instrument_id == instrument_id,
            candles.c.timeframe == timeframe,
            candles.c.trade_date >= first,
            candles.c.trade_date <= last,
        )
        .order_by(candles.c.bar_start)
    ).all()
    step = STEP[timeframe]
    return [Bar(r.bar_start, r.bar_start + step, r.open, r.high, r.low, r.close) for r in rows]


def previous_day_levels(session_bars: Sequence[Bar]) -> DailyLevels | None:
    if not session_bars:
        return None
    return DailyLevels(
        max(b.high for b in session_bars), min(b.low for b in session_bars), session_bars[-1].close
    )


def session_spec(conn: Connection, day: date, previous: date | None) -> SessionSpec:
    s = trading_session(conn, "NSE", day)
    open_, close = (
        s if s else (datetime.combine(day, NORMAL_OPEN, IST), datetime.combine(day, NORMAL_CLOSE, IST))
    )
    prev_open = datetime.combine(previous, NORMAL_OPEN, IST) if previous else None
    return SessionSpec(day, open_, close, prev_open)


def tick_and_lot(conn: Connection, instrument_id: uuid.UUID, on: date) -> tuple[Decimal, int]:
    s = instrument_snapshots
    row = conn.execute(
        select(s.c.tick_size, s.c.lot_size)
        .where(
            s.c.instrument_id == instrument_id,
            s.c.effective_from <= on,
            (s.c.effective_to.is_(None)) | (s.c.effective_to > on),
        )
        .order_by(s.c.effective_from.desc())
        .limit(1)
    ).first()
    return (
        (row.tick_size, row.lot_size) if row else (Decimal("0.05"), 1)
    )  # NSE equity default when unsnapshotted


def load_backtest_inputs(
    conn: Connection,
    source: uuid.UUID,
    members: dict[str, uuid.UUID],
    first_day: date,
    last_day: date,
    lookback_sessions: int,
) -> list[SessionInput]:
    """One `SessionInput` per session in `first_day..last_day` that has 5m bars for at least one member.

    Each symbol's bars are its lookback sessions plus the session itself (earlier bars only), so a replay
    sees exactly what a live run would have had at that time.
    """
    sessions_by_symbol: dict[str, dict[date, list[Bar]]] = {}
    bars15: dict[str, list[Bar]] = {}
    margin = timedelta(days=lookback_sessions * 2 + 7)  # calendar days wide enough for the lookback
    all_days: set[date] = set()
    for sym, iid in members.items():
        five = load_bars(conn, source, iid, "5m", first_day - margin, last_day)
        by_day: dict[date, list[Bar]] = defaultdict(list)
        for b in five:
            by_day[b.start.astimezone(IST).date()].append(b)
        sessions_by_symbol[sym] = by_day
        bars15[sym] = load_bars(conn, source, iid, "15m", first_day - margin, last_day)
        all_days |= {d for d in by_day if first_day <= d <= last_day}
    out: list[SessionInput] = []
    ordered_all = sorted({d for by_day in sessions_by_symbol.values() for d in by_day})
    for day in sorted(all_days):
        idx = ordered_all.index(day)
        window = ordered_all[max(0, idx - lookback_sessions) : idx + 1]
        previous = ordered_all[idx - 1] if idx > 0 else None
        spec = session_spec(conn, day, previous)
        symbols: list[SymbolData] = []
        for sym, by_day in sessions_by_symbol.items():
            if day not in by_day:
                continue
            hist = [b for d in window for b in by_day.get(d, [])]
            horizon = by_day[day][-1].end
            five_bars = [b for b in hist if b.end <= horizon]
            fifteen = [b for b in bars15[sym] if window[0] <= b.start.astimezone(IST).date() <= day]
            tick, lot = tick_and_lot(conn, members[sym], day)
            prev = previous_day_levels(by_day[previous]) if previous and previous in by_day else None
            symbols.append(SymbolData(sym, five_bars, fifteen, prev, tick, lot))
        out.append(SessionInput(spec, symbols))
    return out
