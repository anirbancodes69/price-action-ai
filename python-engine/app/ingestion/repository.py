"""Postgres persistence for intraday ingestion (ENG-05 §9, §12; single writer: ARC-01 §6).

The engine-worker is the writer of ``ingestion_runs``, ``candles`` and ``data_quality_issues``.
Candle corrections are archived by the database trigger (``keep_candle_revision``): this module only
upserts and never sets ``revision``.

Each public method commits its own unit of work, so a crash leaves a ``RUNNING`` run that the next
session-end reconciliation can see, rather than a half-written transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, func, insert, literal_column, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.tables import candles, data_quality_issues, ingestion_runs, instrument_provider_refs
from app.ingestion.fetcher import FetchReport, run_bar_close
from app.ingestion.quality import QualityIssue
from app.ingestion.session import IST
from app.providers.base import (
    MarketDataProvider,
    ProviderBar,
    ProviderContext,
    ProviderInstrumentRef,
    Timeframe,
)

_SEVERITY = {"DUPLICATE": "INFO", "OHLC_INVALID": "ERROR", "PROVIDER_GAP": "ERROR"}
_PK = ["data_source_id", "instrument_id", "timeframe", "bar_start"]


@dataclass(slots=True)
class RunCounters:
    inserted: int = 0
    updated: int = 0


class PgBarStore:
    """``BarStore`` bound to one ingestion run. Upserts by the candle primary key."""

    def __init__(
        self,
        conn: Connection,
        data_source_id: uuid.UUID,
        run_id: uuid.UUID,
        instrument_ids: dict[str, uuid.UUID],
    ) -> None:
        self._conn, self._source, self._run, self._ids = conn, data_source_id, run_id, instrument_ids
        self.counters = RunCounters()

    def save(self, symbol: str, timeframe: Timeframe, bars: list[ProviderBar]) -> None:
        instrument_id = self._ids[symbol]
        for b in bars:
            values: dict[str, Any] = {
                "data_source_id": self._source,
                "instrument_id": instrument_id,
                "timeframe": timeframe,
                "bar_start": b.bar_start,
                "trade_date": b.bar_start.astimezone(IST).date(),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "ingestion_run_id": self._run,
                "revision": 1,
                "updated_at": func.now(),
            }
            ins = pg_insert(candles).values(**values)
            stmt: Any = ins.on_conflict_do_update(
                index_elements=_PK,
                set_={
                    k: ins.excluded[k] for k in ("open", "high", "low", "close", "volume", "ingestion_run_id")
                },
            ).returning(literal_column("(xmax = 0)").label("inserted"))
            if self._conn.execute(stmt).scalar_one():
                self.counters.inserted += 1
            else:
                self.counters.updated += 1
        self._conn.commit()


class IngestionRepository:
    def __init__(self, conn: Connection, data_source_id: uuid.UUID, provider_code: str) -> None:
        self._conn, self._source, self._provider = conn, data_source_id, provider_code

    def resolve_instruments(
        self, refs: Sequence[ProviderInstrumentRef], on: datetime
    ) -> dict[str, uuid.UUID]:
        """Provider token -> ``instrument_id`` valid on ``on`` (ENG-05 §6). Keyed by symbol."""
        day = on.astimezone(IST).date()
        r = instrument_provider_refs
        rows = self._conn.execute(
            select(r.c.provider_token, r.c.instrument_id).where(
                r.c.provider == self._provider,
                r.c.provider_token.in_([x.token for x in refs]),
                r.c.valid_from <= day,
                (r.c.valid_to.is_(None)) | (r.c.valid_to > day),
            )
        ).all()
        by_token = dict(rows)
        return {x.symbol: by_token[x.token] for x in refs if x.token in by_token}

    def begin_run(self, timeframe: Timeframe, bar_start: datetime, total: int) -> uuid.UUID:
        run_id = uuid.uuid4()
        # trade_date stays NULL: uq_ingestion_runs__active is keyed on it and intraday runs are per bar.
        self._conn.execute(
            insert(ingestion_runs).values(
                id=run_id,
                data_source_id=self._source,
                kind="INTRADAY_BARS",
                timeframe=timeframe,
                bar_start=bar_start,
                status="RUNNING",
                instruments_total=total,
                started_at=func.now(),
            )
        )
        self._conn.commit()
        return run_id

    def store(self, run_id: uuid.UUID, instrument_ids: dict[str, uuid.UUID]) -> PgBarStore:
        return PgBarStore(self._conn, self._source, run_id, instrument_ids)

    def finish_run(
        self,
        run_id: uuid.UUID,
        report: FetchReport,
        counters: RunCounters,
        instrument_ids: dict[str, uuid.UUID],
        unmapped: Sequence[str] = (),
    ) -> None:
        rows: list[dict[str, Any]] = []
        for o in report.outcomes:
            rows += [self._issue_row(run_id, instrument_ids[o.symbol], i) for i in o.issues]
        rows += [
            {
                "id": uuid.uuid4(),
                "ingestion_run_id": run_id,
                "instrument_id": None,
                "trade_date": report.bar_start.astimezone(IST).date(),
                "issue_type": "PROVIDER_GAP",
                "severity": "ERROR",
                "details": {"symbol": s, "reason": "no provider reference"},
            }
            for s in unmapped
        ]
        if rows:
            self._conn.execute(insert(data_quality_issues), rows)
        succeeded = sum(1 for o in report.outcomes if o.stored)
        errors = {o.symbol: o.error for o in report.outcomes if o.error}
        summary: dict[str, Any] = {}
        if report.error_code:
            summary["code"] = report.error_code
        if errors:
            summary["instruments"] = errors
        self._conn.execute(
            update(ingestion_runs)
            .where(ingestion_runs.c.id == run_id)
            .values(
                status=report.status,
                instruments_succeeded=succeeded,
                instruments_failed=len(report.outcomes) + len(unmapped) - succeeded,
                rows_inserted=counters.inserted,
                rows_updated=counters.updated,
                quality_issue_count=len(rows),
                error_summary=summary or None,
                finished_at=func.now(),
            )
        )
        self._conn.commit()

    def fail_run(self, run_id: uuid.UUID) -> None:
        """Mark a run FAILED after an unexpected error (the exception is re-raised by the caller)."""
        self._conn.rollback()  # the failed statement may have aborted the transaction
        self._conn.execute(
            update(ingestion_runs)
            .where(ingestion_runs.c.id == run_id)
            .values(status="FAILED", error_summary={"code": "UNEXPECTED_ERROR"}, finished_at=func.now())
        )
        self._conn.commit()

    def _issue_row(self, run_id: uuid.UUID, instrument_id: uuid.UUID, i: QualityIssue) -> dict[str, Any]:
        day = (i.bar_start.astimezone(IST).date()) if i.bar_start else None
        return {
            "id": uuid.uuid4(),
            "ingestion_run_id": run_id,
            "instrument_id": instrument_id,
            "trade_date": day,
            "issue_type": i.type,
            "severity": _SEVERITY.get(i.type, "WARN"),
            "details": {"bar_start": i.bar_start.isoformat() if i.bar_start else None, "detail": i.detail},
        }


def ingest_bar_close(
    repo: IngestionRepository,
    provider: MarketDataProvider,
    ctx: ProviderContext,
    refs: Sequence[ProviderInstrumentRef],
    timeframe: Timeframe,
    bar_start: datetime,
    now: Callable[[], datetime],
    sleep: Callable[[float], None],
) -> FetchReport:
    """One persisted bar-close run: resolve instruments, record the run, fetch, store, finish.

    Instruments without a provider reference are skipped with a ``PROVIDER_GAP`` issue (ENG-05 §6).
    """
    ids = repo.resolve_instruments(refs, bar_start)
    mapped = [r for r in refs if r.symbol in ids]
    unmapped = [r.symbol for r in refs if r.symbol not in ids]
    run_id = repo.begin_run(timeframe, bar_start, len(refs))
    store = repo.store(run_id, ids)
    try:
        report = run_bar_close(provider, ctx, store, mapped, timeframe, bar_start, now, sleep)
    except Exception:
        repo.fail_run(run_id)
        raise
    repo.finish_run(run_id, report, store.counters, ids, unmapped)
    return report
