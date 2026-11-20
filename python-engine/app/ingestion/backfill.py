"""History backfill in provider-sized windows (ENG-05 §12, TRD-06 §3).

Idempotent: candles upsert by their primary key, so a rerun or an overlapping range is safe. Gaps and
quality checks over history are a later step; this stores what the provider returns.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import Connection, func, insert, select, update

from app.db.tables import candles, ingestion_runs
from app.ingestion.repository import IngestionRepository
from app.ingestion.session import IST
from app.providers.base import (
    MarketDataProvider,
    ProviderAuthExpired,
    ProviderContext,
    ProviderError,
    ProviderInstrumentRef,
    Timeframe,
)


def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    """Consecutive inclusive date windows of at most `max_days` calendar days covering `start..end`."""
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        last = min(end, cur + timedelta(days=max_days - 1))
        out.append((cur, last))
        cur = last + timedelta(days=1)
    return out


@dataclass(slots=True)
class BackfillReport:
    run_id: uuid.UUID
    inserted: int = 0
    updated: int = 0
    requests: int = 0
    failed: list[str] = field(default_factory=list)  # "SYMBOL start..end: error class"
    skipped_unmapped: list[str] = field(default_factory=list)
    status: str = "COMPLETED"


def latest_trade_date(
    conn: Connection, source: uuid.UUID, instrument_id: uuid.UUID, timeframe: Timeframe
) -> date | None:
    return conn.execute(
        select(func.max(candles.c.trade_date)).where(
            candles.c.data_source_id == source,
            candles.c.instrument_id == instrument_id,
            candles.c.timeframe == timeframe,
        )
    ).scalar()


def backfill(
    conn: Connection,
    source: uuid.UUID,
    provider: MarketDataProvider,
    ctx: ProviderContext,
    refs: Sequence[ProviderInstrumentRef],
    timeframe: Timeframe,
    start: date,
    end: date,
    sleep: Callable[[float], None],
    resume: bool = True,
    as_of: date | None = None,
) -> BackfillReport:
    """Fetch `timeframe` bars for `refs` over `start..end` and upsert them.

    With `resume`, an instrument that already has bars restarts at its latest stored trade date (that day is
    refetched because it may have been partial). An expired token aborts the run (`FAILED`); other provider
    errors are recorded per instrument window and the run ends `PARTIAL`.

    `as_of` is the date at which provider references are resolved (default `end`). Older history is stored
    under the instruments as they are known today, so a range that ends before the references were opened
    (the first sync) needs a later `as_of`.
    """
    max_days = provider.capabilities().max_days_per_request[timeframe]
    repo = IngestionRepository(conn, source, provider.provider_code)
    ids = repo.resolve_instruments(refs, datetime.combine(as_of or end, time(12), IST))
    report = BackfillReport(uuid.uuid4(), skipped_unmapped=[r.symbol for r in refs if r.symbol not in ids])
    conn.execute(
        insert(ingestion_runs).values(
            id=report.run_id,
            data_source_id=source,
            kind="BACKFILL",
            status="RUNNING",
            range_from=start,
            range_to=end,
            timeframe=timeframe,
            instruments_total=len(refs),
            started_at=func.now(),
        )
    )
    conn.commit()
    store = repo.store(report.run_id, ids)
    done = 0
    try:
        for ref in refs:
            if ref.symbol not in ids:
                continue
            first = start
            if resume:
                last = latest_trade_date(conn, source, ids[ref.symbol], timeframe)
                conn.rollback()
                if last is not None:
                    first = max(start, last)
            ok = True
            for a, b in chunk_ranges(first, end, max_days):
                try:
                    bars = provider.fetch_bars(
                        ctx,
                        ref,
                        timeframe,
                        datetime.combine(a, time(0), IST),
                        datetime.combine(b, time(23, 59, 59), IST),
                    )
                except ProviderAuthExpired:
                    raise
                except ProviderError as exc:
                    report.failed.append(f"{ref.symbol} {a}..{b}: {type(exc).__name__}")
                    ok = False
                    continue
                finally:
                    report.requests += 1
                    sleep(1.0 / provider.capabilities().requests_per_second)
                store.save(ref.symbol, timeframe, bars)
            done += 1 if ok else 0
    except ProviderAuthExpired:
        report.status = "FAILED"
        report.failed.append("auth expired")
    report.inserted, report.updated = store.counters.inserted, store.counters.updated
    if report.status != "FAILED":
        report.status = "PARTIAL" if report.failed or report.skipped_unmapped else "COMPLETED"
    conn.execute(
        update(ingestion_runs)
        .where(ingestion_runs.c.id == report.run_id)
        .values(
            status=report.status,
            instruments_succeeded=done,
            instruments_failed=len(refs) - done,
            rows_inserted=report.inserted,
            rows_updated=report.updated,
            error_summary={"failed": report.failed[:50], "unmapped": report.skipped_unmapped}
            if report.failed or report.skipped_unmapped
            else None,
            finished_at=func.now(),
        )
    )
    conn.commit()
    return report
