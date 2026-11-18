"""Postgres integration for intraday ingestion. Needs a Laravel-migrated database.

Uses ``SCHEMA_DIFF_DATABASE_URL`` (same as the schema-diff test); skipped without it unless
``REQUIRE_SCHEMA_DIFF=1`` (CI). Creates its own rows and deletes them afterwards.
"""

import os
import random
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Connection, create_engine, delete, insert, select

from app.db.tables import (
    candle_revisions,
    candles,
    data_quality_issues,
    data_sources,
    ingestion_runs,
    instrument_provider_refs,
    instruments,
)
from app.ingestion.repository import IngestionRepository, ingest_bar_close
from app.ingestion.session import IST
from app.providers import ProviderBar, ProviderContext, ProviderInstrumentRef
from app.providers.demo import DemoProvider

URL = os.environ.get("SCHEMA_DIFF_DATABASE_URL")
if not URL and os.environ.get("REQUIRE_SCHEMA_DIFF") != "1":
    pytest.skip("SCHEMA_DIFF_DATABASE_URL not set", allow_module_level=True)

# A random past date per test session: a leftover RUNNING run from a crashed session cannot collide.
BAR = datetime(2024, 1, 1, 10, 0, tzinfo=IST) + timedelta(days=random.randint(0, 400))  # noqa: S311
while BAR.weekday() >= 5:  # the DEMO provider has no weekend bars
    BAR += timedelta(days=1)
CTX = ProviderContext("d", lambda: "")


class Fixture:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self.suffix = uuid.uuid4().hex[:8].upper()
        self.created_source = False
        existing = conn.execute(
            select(data_sources.c.id).where(
                data_sources.c.mode == "DEMO",
                data_sources.c.provider == "DEMO",
                data_sources.c.tenant_id.is_(None),
            )
        ).scalar()
        if existing is None:
            existing = uuid.uuid4()
            conn.execute(insert(data_sources).values(id=existing, mode="DEMO", provider="DEMO", name="Demo"))
            self.created_source = True
        self.source: uuid.UUID = existing
        self.instrument_ids: list[uuid.UUID] = []
        self.refs: list[ProviderInstrumentRef] = []
        for n in range(2):
            iid, token = uuid.uuid4(), f"T{self.suffix}{n}"
            conn.execute(
                insert(instruments).values(
                    id=iid,
                    exchange="NSE",
                    segment="EQ",
                    trading_symbol=f"IT{self.suffix}{n}",
                    name="t",
                    status="ACTIVE",
                )
            )
            conn.execute(
                insert(instrument_provider_refs).values(
                    id=uuid.uuid4(),
                    instrument_id=iid,
                    provider="DEMO",
                    provider_token=token,
                    valid_from=BAR.date() - timedelta(days=30),
                )
            )
            self.instrument_ids.append(iid)
            self.refs.append(ProviderInstrumentRef(token, f"DEMO{'AB'[n]}"))
        conn.commit()

    def cleanup(self) -> None:
        c = self.conn
        c.rollback()
        day_start = BAR.replace(hour=0, minute=0)
        runs = select(ingestion_runs.c.id).where(
            ingestion_runs.c.data_source_id == self.source,
            ingestion_runs.c.bar_start >= day_start,
            ingestion_runs.c.bar_start < day_start + timedelta(days=1),
        )
        ids = self.instrument_ids
        c.execute(delete(data_quality_issues).where(data_quality_issues.c.ingestion_run_id.in_(runs)))
        c.execute(delete(candle_revisions).where(candle_revisions.c.instrument_id.in_(ids)))
        c.execute(delete(candles).where(candles.c.instrument_id.in_(ids)))
        c.execute(delete(ingestion_runs).where(ingestion_runs.c.id.in_(runs)))
        c.execute(delete(instrument_provider_refs).where(instrument_provider_refs.c.instrument_id.in_(ids)))
        c.execute(delete(instruments).where(instruments.c.id.in_(ids)))
        if self.created_source:
            c.execute(delete(data_sources).where(data_sources.c.id == self.source))
        c.commit()


@pytest.fixture
def fx() -> Iterator[Fixture]:
    assert URL
    engine = create_engine(URL)
    with engine.connect() as conn:
        f = Fixture(conn)
        try:
            yield f
        finally:
            f.cleanup()
    engine.dispose()


class Clock:
    def __init__(self) -> None:
        self.t = BAR + timedelta(minutes=5)

    def now(self) -> datetime:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += timedelta(seconds=s)


def run(fx: Fixture, provider: DemoProvider, refs: list[ProviderInstrumentRef]):  # type: ignore[no-untyped-def]
    repo = IngestionRepository(fx.conn, fx.source, "DEMO")
    clk = Clock()
    return ingest_bar_close(repo, provider, CTX, refs, "5m", BAR, clk.now, clk.sleep)


def test_run_stores_bars_and_records_the_run(fx: Fixture) -> None:
    report = run(fx, DemoProvider(), fx.refs)
    assert report.status == "COMPLETED"
    rows = fx.conn.execute(select(candles).where(candles.c.instrument_id.in_(fx.instrument_ids))).all()
    assert len(rows) == 2 and all(
        r.timeframe == "5m" and r.bar_start == BAR and r.revision == 1 for r in rows
    )
    assert all(r.trade_date == BAR.date() for r in rows)
    r = fx.conn.execute(
        select(ingestion_runs).where(
            ingestion_runs.c.data_source_id == fx.source, ingestion_runs.c.bar_start == BAR
        )
    ).one()
    assert (r.kind, r.status, r.instruments_total, r.instruments_succeeded, r.rows_inserted) == (
        "INTRADAY_BARS",
        "COMPLETED",
        2,
        2,
        2,
    )
    assert r.finished_at is not None and r.trade_date is None


def test_rerun_is_idempotent_and_a_correction_bumps_the_revision(fx: Fixture) -> None:
    run(fx, DemoProvider(), fx.refs)

    class Corrected(DemoProvider):
        def fetch_bars(self, ctx, ref, timeframe, start, end):  # type: ignore[no-untyped-def]
            return [
                ProviderBar(b.bar_start, b.timeframe, b.open, b.high + Decimal("1"), b.low, b.close, b.volume)
                for b in super().fetch_bars(ctx, ref, timeframe, start, end)
            ]

    run(fx, DemoProvider(), fx.refs)  # same values: nothing changes
    ids = fx.instrument_ids
    assert (
        fx.conn.execute(select(candle_revisions).where(candle_revisions.c.instrument_id.in_(ids))).all() == []
    )
    run(fx, Corrected(), fx.refs)
    revs = fx.conn.execute(select(candles.c.revision).where(candles.c.instrument_id.in_(ids))).scalars().all()
    assert revs == [2, 2]
    assert (
        len(fx.conn.execute(select(candle_revisions).where(candle_revisions.c.instrument_id.in_(ids))).all())
        == 2
    )
    last = fx.conn.execute(
        select(ingestion_runs)
        .where(ingestion_runs.c.bar_start == BAR)
        .order_by(ingestion_runs.c.created_at.desc())
    ).first()
    assert last is not None and last.rows_updated == 2 and last.rows_inserted == 0


def test_unmapped_instrument_is_a_provider_gap_and_late_bar_is_recorded(fx: Fixture) -> None:
    class Late(DemoProvider):
        def fetch_bars(self, ctx, ref, timeframe, start, end):  # type: ignore[no-untyped-def]
            return [] if ref.symbol == "DEMOB" else super().fetch_bars(ctx, ref, timeframe, start, end)

    refs = [*fx.refs, ProviderInstrumentRef("NOPE-" + fx.suffix, "DEMOC")]
    report = run(fx, Late(), refs)
    assert report.status == "PARTIAL"
    run_id = fx.conn.execute(
        select(ingestion_runs.c.id).where(
            ingestion_runs.c.data_source_id == fx.source, ingestion_runs.c.bar_start == BAR
        )
    ).scalar_one()
    issues = fx.conn.execute(
        select(data_quality_issues.c.issue_type, data_quality_issues.c.severity).where(
            data_quality_issues.c.ingestion_run_id == run_id
        )
    ).all()
    assert sorted(issues) == [("LATE_BAR", "WARN"), ("PROVIDER_GAP", "ERROR")]
    r = fx.conn.execute(select(ingestion_runs).where(ingestion_runs.c.id == run_id)).one()
    assert (
        r.status,
        r.instruments_total,
        r.instruments_succeeded,
        r.instruments_failed,
        r.quality_issue_count,
    ) == (
        "PARTIAL",
        3,
        1,
        2,
        2,
    )


def test_run_due_bars_follows_the_calendar_and_is_idempotent(fx: Fixture) -> None:
    from sqlalchemy import func

    from app.db.tables import market_calendar
    from app.ingestion.schedule import run_due_bars

    day = BAR.date()
    fx.conn.execute(
        insert(market_calendar).values(
            exchange="NSE",
            calendar_date=day,
            is_trading_day=True,
            session_open=BAR.replace(hour=9, minute=15).time(),
            session_close=BAR.replace(hour=15, minute=30).time(),
            note="integration test",
        )
    )
    fx.conn.commit()
    try:
        clk = Clock()
        clk.t = BAR.replace(
            hour=9, minute=33
        )  # 5m bars 09:15 and 09:20, 15m bar 09:15 are closed... 09:30 close
        first = run_due_bars(fx.conn, fx.source, DemoProvider(), CTX, fx.refs, clk.now, clk.sleep)
        got = [(r.timeframe, r.bar_start.strftime("%H:%M"), r.status) for r in first]
        assert got == [
            ("5m", "09:15", "COMPLETED"),
            ("5m", "09:20", "COMPLETED"),
            ("5m", "09:25", "COMPLETED"),
            ("15m", "09:15", "COMPLETED"),
        ]
        assert run_due_bars(fx.conn, fx.source, DemoProvider(), CTX, fx.refs, clk.now, clk.sleep) == []
        n = fx.conn.execute(
            select(func.count()).select_from(candles).where(candles.c.instrument_id.in_(fx.instrument_ids))
        ).scalar_one()
        assert n == 2 * 4
        # A day missing from the calendar is not a trading day.
        clk.t = clk.t + timedelta(days=1)
        assert run_due_bars(fx.conn, fx.source, DemoProvider(), CTX, fx.refs, clk.now, clk.sleep) == []
    finally:
        fx.conn.rollback()
        fx.conn.execute(market_calendar.delete().where(market_calendar.c.calendar_date == day))
        fx.conn.commit()
