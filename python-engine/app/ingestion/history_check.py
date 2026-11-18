"""Coverage of stored intraday history against the session grid (TRD-06 §3, ENG-05 §12)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import Connection, select

from app.db.tables import candles
from app.ingestion.session import session_bar_starts
from app.providers.base import Timeframe


@dataclass(frozen=True, slots=True)
class SymbolCoverage:
    symbol: str
    sessions: int  # sessions in the checked range (days where any member has bars)
    complete_sessions: int
    missing_sessions: tuple[date, ...]  # sessions this symbol has no bars on at all
    missing_bars: int
    worst: tuple[tuple[date, int], ...]  # up to five sessions with the most missing bars

    @property
    def coverage_pct(self) -> float:
        return 100.0 * self.complete_sessions / self.sessions if self.sessions else 0.0


@dataclass(frozen=True, slots=True)
class HistoryReport:
    timeframe: str
    first: date | None
    last: date | None
    sessions: int
    symbols: tuple[SymbolCoverage, ...]

    @property
    def clean(self) -> bool:
        return all(s.missing_bars == 0 and not s.missing_sessions for s in self.symbols)


def missing_starts(
    day: date, timeframe: Timeframe, present: set[datetime], close: time | None
) -> list[datetime]:
    """Expected bar starts of a normal session that are not stored."""
    return [t for t in session_bar_starts(day, timeframe, close) if t not in present]


def stored_starts(
    conn: Connection,
    source: uuid.UUID,
    instrument_id: uuid.UUID,
    timeframe: Timeframe,
    first: date,
    last: date,
) -> dict[date, set[datetime]]:
    rows = conn.execute(
        select(candles.c.trade_date, candles.c.bar_start).where(
            candles.c.data_source_id == source,
            candles.c.instrument_id == instrument_id,
            candles.c.timeframe == timeframe,
            candles.c.trade_date >= first,
            candles.c.trade_date <= last,
        )
    ).all()
    out: dict[date, set[datetime]] = defaultdict(set)
    for d, ts in rows:
        out[d].add(ts)
    return out


def history_report(
    conn: Connection,
    source: uuid.UUID,
    members: Mapping[str, uuid.UUID],
    timeframe: Timeframe,
    first: date,
    last: date,
    close: time | None = None,
) -> HistoryReport:
    """Per-symbol completeness. A session is any day on which at least one member has bars, because the
    holiday calendar is not loaded; a symbol with none that day is reported as a missing session."""
    per_symbol = {s: stored_starts(conn, source, iid, timeframe, first, last) for s, iid in members.items()}
    sessions = sorted({d for days in per_symbol.values() for d in days})
    out: list[SymbolCoverage] = []
    for sym in sorted(per_symbol):
        days = per_symbol[sym]
        missing_days = tuple(d for d in sessions if d not in days)
        gaps = {d: len(missing_starts(d, timeframe, present, close)) for d, present in days.items()}
        bad = {d: n for d, n in gaps.items() if n}
        out.append(
            SymbolCoverage(
                sym,
                len(sessions),
                len(sessions) - len(missing_days) - len(bad),
                missing_days,
                sum(bad.values()),
                tuple(sorted(bad.items(), key=lambda kv: (-kv[1], kv[0]))[:5]),
            )
        )
    return HistoryReport(
        timeframe,
        sessions[0] if sessions else None,
        sessions[-1] if sessions else None,
        len(sessions),
        tuple(out),
    )
