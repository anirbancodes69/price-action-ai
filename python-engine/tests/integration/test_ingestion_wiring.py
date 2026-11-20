"""Instrument sync, universe loader, backfill and backtest loader against Postgres.

Needs a Laravel-migrated database and a role that may write the Laravel-owned `universes` and
`data_sources` tables. Uses ``SCHEMA_DIFF_DATABASE_URL``; skipped without it unless ``REQUIRE_SCHEMA_DIFF=1``.
Creates its own rows (random symbols) and deletes them afterwards.
"""

from __future__ import annotations

import os
import random
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Connection, create_engine, delete, insert, select

from app.backtest.loader import load_backtest_inputs
from app.db.tables import (
    candle_revisions,
    candles,
    data_sources,
    ingestion_runs,
    instrument_provider_refs,
    instrument_snapshots,
    instruments,
    universe_memberships,
    universes,
)
from app.ingestion.backfill import backfill
from app.ingestion.instruments import sync_instruments
from app.ingestion.session import IST
from app.ingestion.universe import UnknownUniverse, load_universe, universe_refs
from app.providers.base import (
    ProviderAuthExpired,
    ProviderBar,
    ProviderCapabilities,
    ProviderContext,
    ProviderInstrument,
    ProviderInstrumentRef,
    ProviderUnavailable,
    Timeframe,
)

URL = os.environ.get("SCHEMA_DIFF_DATABASE_URL")
if not URL and os.environ.get("REQUIRE_SCHEMA_DIFF") != "1":
    pytest.skip("SCHEMA_DIFF_DATABASE_URL not set", allow_module_level=True)

D = Decimal
CTX = ProviderContext("d", lambda: "")
# Random past weekdays far from real data; the instruments are new, so candles cannot collide anyway.
DAY0 = date(2023, 1, 2) + timedelta(days=random.randint(0, 300))  # noqa: S311
while DAY0.weekday() != 0:
    DAY0 += timedelta(days=1)
DAYS = [DAY0 + timedelta(days=i) for i in range(3)]  # Mon, Tue, Wed


def five_minute_bars(day: date, base: str = "100") -> list[ProviderBar]:
    open_ = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    return [
        ProviderBar(open_ + timedelta(minutes=5 * i), "5m", D(base), D(base) + 1, D(base) - 1, D(base), 1000)
        for i in range(75)
    ]


class FakeProvider:
    provider_code = "DEMO"

    def __init__(self, symbols: list[str], suffix: str) -> None:
        self.symbols, self.suffix = symbols, suffix
        self.tick = D("0.05")
        self.token_shift = ""
        self.fail_symbol: str | None = None
        self.expired = False
        self.corrupt_first_bar = False

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(("5m", "15m"), {"5m": 2, "15m": 2}, 1000.0, False)

    def fetch_instruments(self, ctx: ProviderContext) -> list[ProviderInstrument]:
        return [
            ProviderInstrument(
                ProviderInstrumentRef(f"{self.suffix}{n}{self.token_shift}", s),
                f"{s} Ltd",
                "NSE",
                "NSE",
                self.tick,
                1,
                False,
            )
            for n, s in enumerate(self.symbols)
        ]

    def fetch_bars(
        self,
        ctx: ProviderContext,
        ref: ProviderInstrumentRef,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[ProviderBar]:
        if self.expired:
            raise ProviderAuthExpired("expired")
        if ref.symbol == self.fail_symbol:
            raise ProviderUnavailable("down")
        out: list[ProviderBar] = []
        day = start.astimezone(IST).date()
        while day <= end.astimezone(IST).date():
            if day.weekday() < 5 and timeframe == "5m":
                # price level encodes the weekday so the previous-day levels are checkable
                out += five_minute_bars(day, str(100 + day.weekday() * 10))
            day += timedelta(days=1)
        if self.corrupt_first_bar and out:
            b = out[0]  # a high below the open: what Kite returned for one real bar
            out[0] = ProviderBar(b.bar_start, b.timeframe, b.open, b.open - 5, b.low, b.close, b.volume)
        return out


class Fx:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self.suffix = uuid.uuid4().hex[:8].upper()
        self.symbols = [f"WT{self.suffix}{n}" for n in range(3)]
        self.provider = FakeProvider(self.symbols, self.suffix)
        existing = conn.execute(
            select(data_sources.c.id).where(
                data_sources.c.mode == "DEMO",
                data_sources.c.provider == "DEMO",
                data_sources.c.tenant_id.is_(None),
            )
        ).scalar()
        self.created_source = existing is None
        self.source: uuid.UUID = existing or uuid.uuid4()
        if self.created_source:
            conn.execute(
                insert(data_sources).values(id=self.source, mode="DEMO", provider="DEMO", name="Demo")
            )
        # Universe codes are a fixed set (ck_universes__code). Use a real one that is empty, and never touch a
        # universe that already has members (the loader makes memberships equal the given list).
        self.universe_code = "NIFTYMIDCAP150"
        row = conn.execute(select(universes.c.id).where(universes.c.code == self.universe_code)).scalar()
        self.created_universe = row is None
        self.universe_id: uuid.UUID = row or uuid.uuid4()
        if self.created_universe:
            conn.execute(
                insert(universes).values(
                    id=self.universe_id, code=self.universe_code, name="NIFTY Midcap 150", is_demo=False
                )
            )
        elif conn.execute(
            select(universe_memberships.c.id)
            .where(universe_memberships.c.universe_id == self.universe_id)
            .limit(1)
        ).first():
            conn.rollback()
            pytest.skip(f"universe {self.universe_code} already has members; not touching it")
        conn.commit()
        self.run_ids: list[uuid.UUID] = []

    def instrument_ids(self) -> dict[str, uuid.UUID]:
        rows = self.conn.execute(
            select(instruments.c.trading_symbol, instruments.c.id).where(
                instruments.c.trading_symbol.in_(self.symbols)
            )
        ).all()
        return dict(rows)

    def cleanup(self) -> None:
        c = self.conn
        c.rollback()
        ids = list(self.instrument_ids().values())
        c.execute(delete(candle_revisions).where(candle_revisions.c.instrument_id.in_(ids)))
        c.execute(delete(candles).where(candles.c.instrument_id.in_(ids)))
        if self.run_ids:
            c.execute(delete(ingestion_runs).where(ingestion_runs.c.id.in_(self.run_ids)))
        c.execute(delete(universe_memberships).where(universe_memberships.c.universe_id == self.universe_id))
        if self.created_universe:
            c.execute(delete(universes).where(universes.c.id == self.universe_id))
        c.execute(delete(instrument_snapshots).where(instrument_snapshots.c.instrument_id.in_(ids)))
        c.execute(delete(instrument_provider_refs).where(instrument_provider_refs.c.instrument_id.in_(ids)))
        c.execute(delete(instruments).where(instruments.c.id.in_(ids)))
        if self.created_source:
            c.execute(delete(data_sources).where(data_sources.c.id == self.source))
        c.commit()


@pytest.fixture
def fx() -> Iterator[Fx]:
    assert URL
    engine = create_engine(URL)
    with engine.connect() as conn:
        f = Fx(conn)
        try:
            yield f
        finally:
            f.cleanup()
    engine.dispose()


def test_sync_instruments_is_idempotent_and_tracks_changes(fx: Fx) -> None:
    on = DAYS[0]
    r = sync_instruments(fx.conn, fx.provider, CTX, [*fx.symbols, "NOSUCHSYMBOL"], on)
    assert (r.created, r.refs_added, r.snapshots_added, r.missing) == (3, 3, 3, ("NOSUCHSYMBOL",))
    again = sync_instruments(fx.conn, fx.provider, CTX, fx.symbols, on)
    assert (again.created, again.refs_added, again.snapshots_added) == (0, 0, 0)
    # a new provider token closes the old reference and opens a new one
    fx.provider.token_shift = "X"
    later = on + timedelta(days=1)
    r2 = sync_instruments(fx.conn, fx.provider, CTX, fx.symbols, later)
    assert r2.refs_added == 3 and r2.snapshots_added == 0
    closed = fx.conn.execute(
        select(instrument_provider_refs.c.valid_to).where(
            instrument_provider_refs.c.instrument_id.in_(fx.instrument_ids().values()),
            instrument_provider_refs.c.valid_to.is_not(None),
        )
    ).all()
    assert len(closed) == 3 and all(row.valid_to == later for row in closed)
    # a changed tick size gets a new snapshot
    fx.provider.tick = D("0.01")
    assert (
        sync_instruments(fx.conn, fx.provider, CTX, fx.symbols, later + timedelta(days=1)).snapshots_added
        == 3
    )


def test_universe_loader_and_refs(fx: Fx) -> None:
    on = DAYS[0]
    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols, on)
    a, b, c = fx.symbols
    r = load_universe(fx.conn, fx.universe_code, [a, b, "NOSUCHSYMBOL"], on)
    assert (r.added, r.closed, r.unchanged, r.unknown) == (2, 0, 0, ("NOSUCHSYMBOL",))
    assert load_universe(fx.conn, fx.universe_code, [a, b], on).unchanged == 2
    assert [x.symbol for x in universe_refs(fx.conn, fx.universe_code, "DEMO", on)] == [a, b]
    # a rebalance a day later: b leaves, c joins
    nxt = on + timedelta(days=1)
    r2 = load_universe(fx.conn, fx.universe_code, [a, c], nxt)
    assert (r2.added, r2.closed, r2.unchanged) == (1, 1, 1)
    assert [x.symbol for x in universe_refs(fx.conn, fx.universe_code, "DEMO", nxt)] == [a, c]
    assert [x.symbol for x in universe_refs(fx.conn, fx.universe_code, "DEMO", on)] == [a, b]  # point in time
    # removal dated on the day it joined cannot be recorded (range check): reported, not raised
    r3 = load_universe(fx.conn, fx.universe_code, [a], nxt)
    assert (r3.not_closed == (c,) and r3.closed == 0) or r3.closed == 1  # b already closed, c joined on `nxt`
    with pytest.raises(UnknownUniverse):
        load_universe(fx.conn, "NO_SUCH_UNIVERSE", [a], on)


def test_backfill_chunks_resumes_and_reports(fx: Fx) -> None:
    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols[:2], DAYS[0] - timedelta(days=5))
    refs = [ProviderInstrumentRef(f"{fx.suffix}{n}", s) for n, s in enumerate(fx.symbols[:2])]
    sleeps: list[float] = []
    rep = backfill(fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], sleeps.append)
    fx.run_ids.append(rep.run_id)
    assert rep.status == "COMPLETED" and rep.inserted == 2 * 3 * 75 and rep.updated == 0
    assert rep.requests == 2 * 2  # 3 days in windows of 2 -> 2 requests per instrument
    # resume: restarts at the latest stored day (refetched, so updated rows, nothing new)
    again = backfill(fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None)
    fx.run_ids.append(again.run_id)
    assert (again.inserted, again.updated, again.status) == (0, 2 * 75, "COMPLETED")
    # provider trouble on one instrument: PARTIAL with the failure recorded; others still stored
    fx.provider.fail_symbol = fx.symbols[1]
    part = backfill(
        fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None, resume=False
    )
    fx.run_ids.append(part.run_id)
    assert part.status == "PARTIAL" and part.failed and fx.symbols[1] in part.failed[0]
    # an expired token aborts the run
    fx.provider.fail_symbol, fx.provider.expired = None, True
    dead = backfill(
        fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None, resume=False
    )
    fx.run_ids.append(dead.run_id)
    assert dead.status == "FAILED"
    row = fx.conn.execute(
        select(ingestion_runs.c.status, ingestion_runs.c.kind).where(ingestion_runs.c.id == dead.run_id)
    ).one()
    assert (row.status, row.kind) == ("FAILED", "BACKFILL")
    # unmapped instruments are skipped and reported
    fx.provider.expired = False
    ghost = backfill(
        fx.conn,
        fx.source,
        fx.provider,
        CTX,
        [ProviderInstrumentRef("nope", "GHOST")],
        "5m",
        DAYS[0],
        DAYS[0],
        lambda _: None,
    )
    fx.run_ids.append(ghost.run_id)
    assert ghost.skipped_unmapped == ["GHOST"] and ghost.status == "PARTIAL"


def test_backfill_of_history_older_than_the_first_sync_needs_as_of(fx: Fx) -> None:
    synced = DAYS[2] + timedelta(days=1)  # the provider references open after the history being fetched
    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols[:1], synced)
    refs = [ProviderInstrumentRef(f"{fx.suffix}0", fx.symbols[0])]
    miss = backfill(fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None)
    fx.run_ids.append(miss.run_id)
    assert miss.skipped_unmapped == [fx.symbols[0]] and miss.inserted == 0
    got = backfill(
        fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None, as_of=synced
    )
    fx.run_ids.append(got.run_id)
    assert got.status == "COMPLETED" and got.inserted == 3 * 75


def test_backfill_rejects_a_corrupt_bar_instead_of_failing_the_run(fx: Fx) -> None:
    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols[:1], DAYS[0] - timedelta(days=5))
    refs = [ProviderInstrumentRef(f"{fx.suffix}0", fx.symbols[0])]
    fx.provider.corrupt_first_bar = True
    rep = backfill(fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[0], lambda _: None)
    fx.run_ids.append(rep.run_id)
    assert rep.status == "PARTIAL" and not rep.failed
    assert len(rep.rejected_bars) == 1 and "OHLC out of order" in rep.rejected_bars[0]
    assert rep.inserted == 74  # the other 74 bars of the day are stored


def test_backtest_loader_builds_sessions_with_previous_day_levels(fx: Fx) -> None:
    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols[:1], DAYS[0] - timedelta(days=5))
    refs = [ProviderInstrumentRef(f"{fx.suffix}0", fx.symbols[0])]
    fx.run_ids.append(
        backfill(fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None).run_id
    )
    members = fx.instrument_ids()
    inputs = load_backtest_inputs(fx.conn, fx.source, members, DAYS[1], DAYS[2], lookback_sessions=1)
    assert [i.spec.session_date for i in inputs] == [DAYS[1], DAYS[2]]
    tue = inputs[0]
    [s] = tue.symbols
    assert s.symbol == fx.symbols[0] and (s.tick, s.lot_size) == (D("0.05"), 1)
    # Monday's bars sit at 100 + weekday x 10 = 100 (high 101, low 99, close 100)
    assert s.prev_day is not None and (s.prev_day.high, s.prev_day.low, s.prev_day.close) == (
        D(101),
        D(99),
        D(100),
    )
    # lookback 1: Monday (75 bars) + Tuesday (75 bars); never later bars
    assert len(s.bars_5m) == 150 and s.bars_5m[-1].start.astimezone(IST).date() == DAYS[1]
    assert (
        tue.spec.session_open.astimezone(IST).time().hour,
        tue.spec.session_close.astimezone(IST).time().hour,
    ) == (9, 15)
    assert UTC is not None


def test_history_report_stale_recovery_and_reconcile(fx: Fx) -> None:
    from datetime import time as dtime

    from app.ingestion.history_check import history_report
    from app.ingestion.reconcile import already_reconciled, reconcile_day, recover_stale_runs
    from app.ingestion.universe import universe_members

    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols[:2], DAYS[0] - timedelta(days=5))
    load_universe(fx.conn, fx.universe_code, fx.symbols[:2], DAYS[0] - timedelta(days=5))
    refs = [ProviderInstrumentRef(f"{fx.suffix}{n}", s) for n, s in enumerate(fx.symbols[:2])]
    ids = fx.instrument_ids()
    members = universe_members(fx.conn, fx.universe_code, DAYS[0])
    assert set(members) == set(fx.symbols[:2])
    # store Monday fully for A, and for B only a part of Monday; Tuesday only for A
    fx.run_ids.append(
        backfill(
            fx.conn, fx.source, fx.provider, CTX, refs[:1], "5m", DAYS[0], DAYS[1], lambda _: None
        ).run_id
    )
    part = backfill(fx.conn, fx.source, fx.provider, CTX, refs[1:], "5m", DAYS[0], DAYS[0], lambda _: None)
    fx.run_ids.append(part.run_id)
    fx.conn.execute(
        delete(candles).where(
            candles.c.instrument_id == ids[fx.symbols[1]],
            candles.c.bar_start >= datetime.combine(DAYS[0], dtime(14, 0), IST),
        )
    )
    fx.conn.commit()
    rep = history_report(fx.conn, fx.source, members, "5m", DAYS[0], DAYS[1])
    by = {s.symbol: s for s in rep.symbols}
    assert rep.sessions == 2 and not rep.clean
    a, b = by[fx.symbols[0]], by[fx.symbols[1]]
    assert (a.missing_bars, a.missing_sessions) == (0, ())
    assert (
        b.missing_sessions == (DAYS[1],) and b.missing_bars == 18
    )  # 14:00 .. 15:25 on the full 75-bar grid (no provider cutoff given)
    # reconcile Monday: B is refetched from the provider and healed
    rec = reconcile_day(fx.conn, fx.source, fx.provider, CTX, refs, ids, DAYS[0], lambda _: None)
    fx.run_ids += [
        r
        for (r,) in fx.conn.execute(
            select(ingestion_runs.c.id).where(
                ingestion_runs.c.kind == "BACKFILL", ingestion_runs.c.range_from == DAYS[0]
            )
        ).all()
        if r not in fx.run_ids
    ]
    assert rec.refetched and rec.gaps_before > 0
    # the fake provider serves a full 09:15-15:10 grid, the Kite-style close is 15:15; 75 bars include 15:15-15:25
    assert already_reconciled(fx.conn, fx.source, DAYS[0])
    # stale RUNNING runs are failed, fresh ones are not
    old, fresh = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC)
    for rid, started in ((old, now - timedelta(hours=2)), (fresh, now)):
        fx.conn.execute(
            insert(ingestion_runs).values(
                id=rid,
                data_source_id=fx.source,
                kind="BACKFILL",
                status="RUNNING",
                range_from=DAYS[2],
                range_to=DAYS[2],
                timeframe="5m",
                instruments_total=1,
                started_at=started,
            )
        )
        fx.run_ids.append(rid)
    fx.conn.commit()
    assert recover_stale_runs(fx.conn, fx.source, now) >= 1
    st = dict(
        fx.conn.execute(
            select(ingestion_runs.c.id, ingestion_runs.c.status).where(ingestion_runs.c.id.in_([old, fresh]))
        ).all()
    )
    assert st == {old: "FAILED", fresh: "RUNNING"}


def test_symbol_snapshot_as_of(fx: Fx) -> None:
    from app.analysis.snapshot import latest_bar_end, load_symbol_snapshot

    sync_instruments(fx.conn, fx.provider, CTX, fx.symbols[:2], DAYS[0] - timedelta(days=5))
    refs = [ProviderInstrumentRef(f"{fx.suffix}0", fx.symbols[0])]
    fx.run_ids.append(
        backfill(fx.conn, fx.source, fx.provider, CTX, refs, "5m", DAYS[0], DAYS[2], lambda _: None).run_id
    )
    ids = fx.instrument_ids()
    a, b = ids[fx.symbols[0]], ids[fx.symbols[1]]
    assert load_symbol_snapshot(fx.conn, fx.source, b, fx.symbols[1], 1) is None  # no bars stored
    sym, spec = load_symbol_snapshot(fx.conn, fx.source, a, fx.symbols[0], 1)  # type: ignore[misc]
    assert spec.session_date == DAYS[2] and len(sym.bars_5m) == 150  # Tuesday + Wednesday
    # Tuesday's bars sit at 100 + 1 x 10 = 110 (high 111, low 109, close 110)
    assert sym.prev_day is not None and (sym.prev_day.high, sym.prev_day.low, sym.prev_day.close) == (
        D(111),
        D(109),
        D(110),
    )
    # as of Tuesday 10:00 IST: only bars that ended by then, previous session is Monday (level 100)
    asof = datetime(DAYS[1].year, DAYS[1].month, DAYS[1].day, 10, 0, tzinfo=IST)
    assert latest_bar_end(fx.conn, fx.source, a, asof) == asof
    past, pspec = load_symbol_snapshot(fx.conn, fx.source, a, fx.symbols[0], 1, asof)  # type: ignore[misc]
    assert pspec.session_date == DAYS[1] and len(past.bars_5m) == 75 + 9
    assert past.bars_5m[-1].end == asof
    assert past.prev_day is not None and (past.prev_day.high, past.prev_day.low) == (D(101), D(99))
