"""Stale-run recovery and session-end reconciliation (ENG-05 §12 recovery).

A crash can leave a run `RUNNING`, which blocks that bar (unique active-run index). A provider hiccup can
leave holes in a session. Both are repaired here without inventing data: holes are refetched from the
provider, and what is still missing afterwards is reported.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import Connection, func, select, update

from app.db.tables import ingestion_runs
from app.ingestion.backfill import backfill
from app.ingestion.history_check import missing_starts, stored_starts
from app.ingestion.schedule import TIMEFRAMES, trading_session
from app.ingestion.session import IST
from app.providers.base import MarketDataProvider, ProviderContext, ProviderInstrumentRef

STALE_AFTER = timedelta(minutes=30)  # HYPOTHESIS: a bar-close run never legitimately lasts this long
RECONCILE_WINDOW = timedelta(hours=3)  # keep trying after the close for this long


def recover_stale_runs(
    conn: Connection, source: uuid.UUID, now: datetime, older_than: timedelta = STALE_AFTER
) -> int:
    """Mark `RUNNING` runs started before `now - older_than` as `FAILED` (code `STALE_RUN`)."""
    res = conn.execute(
        update(ingestion_runs)
        .where(
            ingestion_runs.c.data_source_id == source,
            ingestion_runs.c.status == "RUNNING",
            ingestion_runs.c.started_at < now - older_than,
        )
        .values(status="FAILED", error_summary={"code": "STALE_RUN"}, finished_at=func.now())
    )
    conn.commit()
    return res.rowcount


@dataclass(slots=True)
class ReconcileReport:
    day: date
    gaps_before: int = 0
    gaps_after: int = 0
    refetched: list[str] = field(default_factory=list)  # "SYMBOL tf"
    still_missing: list[str] = field(default_factory=list)  # "SYMBOL tf: n bars"


def _gaps(
    conn: Connection,
    source: uuid.UUID,
    ids: Mapping[str, uuid.UUID],
    refs: Sequence[ProviderInstrumentRef],
    day: date,
    close: time | None,
) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for tf in TIMEFRAMES:
        for r in refs:
            if r.symbol not in ids:
                continue
            present = stored_starts(conn, source, ids[r.symbol], tf, day, day).get(day, set())
            n = len(missing_starts(day, tf, present, close))
            if n:
                out[(r.symbol, tf)] = n
    conn.rollback()
    return out


def reconcile_day(
    conn: Connection,
    source: uuid.UUID,
    provider: MarketDataProvider,
    ctx: ProviderContext,
    refs: Sequence[ProviderInstrumentRef],
    ids: Mapping[str, uuid.UUID],
    day: date,
    sleep: Callable[[float], None],
) -> ReconcileReport:
    """Refetch the day's bars for every instrument and timeframe that has holes, then recheck."""
    close = provider.capabilities().intraday_close
    rep = ReconcileReport(day)
    before = _gaps(conn, source, ids, refs, day, close)
    rep.gaps_before = sum(before.values())
    for tf in TIMEFRAMES:
        todo = [r for r in refs if (r.symbol, tf) in before]
        if todo:
            backfill(conn, source, provider, ctx, todo, tf, day, day, sleep, resume=False)
            rep.refetched += [f"{r.symbol} {tf}" for r in todo]
    after = _gaps(conn, source, ids, refs, day, close) if before else {}
    rep.gaps_after = sum(after.values())
    rep.still_missing = [f"{s} {tf}: {n} bars" for (s, tf), n in sorted(after.items())]
    return rep


def reconciliation_due(session: tuple[datetime, datetime] | None, now: datetime) -> bool:
    """True between the session close and `RECONCILE_WINDOW` after it."""
    if session is None:
        return False
    return session[1] <= now < session[1] + RECONCILE_WINDOW


def already_reconciled(conn: Connection, source: uuid.UUID, day: date) -> bool:
    """A `BACKFILL` run for exactly this day exists (reconciliation writes one when it refetches)."""
    found = conn.execute(
        select(ingestion_runs.c.id)
        .where(
            ingestion_runs.c.data_source_id == source,
            ingestion_runs.c.kind == "BACKFILL",
            ingestion_runs.c.range_from == day,
            ingestion_runs.c.range_to == day,
            ingestion_runs.c.status.in_(("COMPLETED", "PARTIAL")),
        )
        .limit(1)
    ).first()
    conn.rollback()
    return found is not None


def run_maintenance(
    conn: Connection,
    source: uuid.UUID,
    provider: MarketDataProvider,
    ctx: ProviderContext,
    refs: Sequence[ProviderInstrumentRef],
    ids: Mapping[str, uuid.UUID],
    now: datetime,
    sleep: Callable[[float], None],
    exchange: str = "NSE",
) -> tuple[int, ReconcileReport | None]:
    """Stale-run recovery every call; reconciliation once the session has closed and holes exist."""
    stale = recover_stale_runs(conn, source, now)
    day = now.astimezone(IST).date()
    session = trading_session(conn, exchange, day)
    conn.rollback()
    if reconciliation_due(session, now) and not already_reconciled(conn, source, day):
        return stale, reconcile_day(conn, source, provider, ctx, refs, ids, day, sleep)
    return stale, None
