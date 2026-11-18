"""Bar-close scheduling (ENG-05 §12 steps 1-2).

``due_bars`` is pure. ``run_due_bars`` reads the calendar and the last processed bar from Postgres and
runs the persisted bar-close ingestion for every due bar. It is meant to be called once a minute by a
worker cron job; that wiring waits for the universe loader and the Kite token supplier (ARC-06 §5).

Gaps older than ``MAX_CATCHUP`` bars are left to the session-end reconciliation.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta

from sqlalchemy import Connection, func, select
from sqlalchemy.exc import IntegrityError

from app.db.tables import ingestion_runs, market_calendar
from app.ingestion.fetcher import FetchReport
from app.ingestion.repository import IngestionRepository, ingest_bar_close
from app.ingestion.session import IST, bar_minutes
from app.providers.base import MarketDataProvider, ProviderContext, ProviderInstrumentRef, Timeframe

TIMEFRAMES: tuple[Timeframe, ...] = ("5m", "15m")  # 5m first: the 15m consistency check needs it
MAX_CATCHUP = 3  # HYPOTHESIS: most recent closed bars retried per timeframe per tick
PROCESSED = ("COMPLETED", "PARTIAL")  # FAILED bars are retried while inside the catch-up window


def due_bars(
    now: datetime,
    session: tuple[datetime, datetime] | None,
    last: dict[Timeframe, datetime | None],
    max_catchup: int = MAX_CATCHUP,
) -> list[tuple[Timeframe, datetime]]:
    """Bars of today's session that have closed by ``now`` and are newer than ``last``.

    Ordered by bar close, 5m before 15m. At most ``max_catchup`` most recent bars per timeframe.
    """
    if session is None:
        return []
    open_, close = session
    out: list[tuple[Timeframe, datetime]] = []
    for tf in TIMEFRAMES:
        step = timedelta(minutes=bar_minutes(tf))
        floor = last.get(tf)
        starts: list[datetime] = []
        cur = open_
        while cur + step <= min(close, now):
            if floor is None or cur > floor:
                starts.append(cur)
            cur += step
        out += [(tf, s) for s in starts[-max_catchup:]]
    return sorted(out, key=lambda x: (x[1] + timedelta(minutes=bar_minutes(x[0])), TIMEFRAMES.index(x[0])))


def trading_session(conn: Connection, exchange: str, day: date) -> tuple[datetime, datetime] | None:
    """The session of ``day`` from ``market_calendar``; ``None`` on a non-trading or unknown day."""
    row = conn.execute(
        select(
            market_calendar.c.is_trading_day, market_calendar.c.session_open, market_calendar.c.session_close
        ).where(market_calendar.c.exchange == exchange, market_calendar.c.calendar_date == day)
    ).first()
    if row is None or not row.is_trading_day or row.session_open is None or row.session_close is None:
        return None
    return datetime.combine(day, row.session_open, IST), datetime.combine(day, row.session_close, IST)


def last_processed(
    conn: Connection, data_source_id: uuid.UUID, timeframe: Timeframe, day: date
) -> datetime | None:
    start = datetime.combine(day, datetime.min.time(), IST)
    return conn.execute(
        select(func.max(ingestion_runs.c.bar_start)).where(
            ingestion_runs.c.data_source_id == data_source_id,
            ingestion_runs.c.kind == "INTRADAY_BARS",
            ingestion_runs.c.timeframe == timeframe,
            ingestion_runs.c.status.in_(PROCESSED),
            ingestion_runs.c.bar_start >= start,
            ingestion_runs.c.bar_start < start + timedelta(days=1),
        )
    ).scalar()


def run_due_bars(
    conn: Connection,
    data_source_id: uuid.UUID,
    provider: MarketDataProvider,
    ctx: ProviderContext,
    refs: Sequence[ProviderInstrumentRef],
    now: Callable[[], datetime],
    sleep: Callable[[float], None],
    exchange: str = "NSE",
) -> list[FetchReport]:
    """Ingest every bar that is due. Idempotent: a bar already processed is not fetched again."""
    t = now()
    day = t.astimezone(IST).date()
    last: dict[Timeframe, datetime | None] = {
        tf: last_processed(conn, data_source_id, tf, day) for tf in TIMEFRAMES
    }
    conn.rollback()  # end the read transaction; the repository commits its own units of work
    repo = IngestionRepository(conn, data_source_id, provider.provider_code)
    reports: list[FetchReport] = []
    for tf, start in due_bars(t, trading_session(conn, exchange, day), last):
        try:
            reports.append(ingest_bar_close(repo, provider, ctx, refs, tf, start, now, sleep))
        except IntegrityError:
            conn.rollback()  # a run for this bar is already active: another process owns it
    return reports
