"""Pure parts of the ingestion wiring: symbol files, token supplier, chunking, worker config."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.backtest.loader import previous_day_levels
from app.domain.types import Bar
from app.ingestion.backfill import chunk_ranges
from app.ingestion.universe import parse_symbols
from app.providers.base import ProviderAuthExpired
from app.providers.demo import DemoProvider
from app.providers.kite.token import FileTokenSupplier, next_expiry
from app.settings import Settings
from app.workers.ingest import build_provider, ingest_once
from app.workers.settings import WorkerSettings

IST_OFFSET_UTC = {"06:00": (0, 30)}  # 06:00 IST = 00:30 UTC


def test_parse_symbols_plain_list_and_csv() -> None:
    assert parse_symbols("# header\nreliance\n TCS \n\nreliance\n") == ["RELIANCE", "TCS"]
    csv_text = (
        "Company Name,Industry,Symbol,Series,ISIN Code\nReliance,Oil,RELIANCE,EQ,X\nTCS Ltd,IT,tcs,EQ,Y\n"
    )
    assert parse_symbols(csv_text) == ["RELIANCE", "TCS"]
    assert parse_symbols("") == []


def test_next_expiry_is_the_next_0600_ist() -> None:
    # 2026-11-18 03:00 UTC = 08:30 IST -> expires 2026-11-19 06:00 IST = 00:30 UTC
    assert next_expiry(datetime(2026, 11, 18, 3, 0, tzinfo=UTC)) == datetime(2026, 11, 19, 0, 30, tzinfo=UTC)
    # written at 05:59 IST (00:29 UTC) -> expires one minute later
    assert next_expiry(datetime(2026, 11, 18, 0, 29, tzinfo=UTC)) == datetime(2026, 11, 18, 0, 30, tzinfo=UTC)
    # written exactly at 06:00 IST -> the next day
    assert next_expiry(datetime(2026, 11, 18, 0, 30, tzinfo=UTC)) == datetime(2026, 11, 19, 0, 30, tzinfo=UTC)


def _token(tmp_path: Path, written: datetime, body: str = "tok123\n") -> Path:
    p = tmp_path / ".kite_token"
    p.write_text(body)
    os.utime(p, (written.timestamp(), written.timestamp()))
    return p


def test_token_supplier_returns_a_fresh_token(tmp_path: Path) -> None:
    written = datetime(2026, 11, 18, 3, 0, tzinfo=UTC)
    p = _token(tmp_path, written)
    sup = FileTokenSupplier(p, now=lambda: datetime(2026, 11, 18, 9, 0, tzinfo=UTC))
    assert sup() == "tok123"


def test_token_supplier_rejects_expired_missing_and_empty(tmp_path: Path) -> None:
    written = datetime(2026, 11, 18, 3, 0, tzinfo=UTC)
    p = _token(tmp_path, written)
    late = FileTokenSupplier(p, now=lambda: datetime(2026, 11, 19, 0, 30, tzinfo=UTC))  # exactly the expiry
    with pytest.raises(ProviderAuthExpired):
        late()
    with pytest.raises(ProviderAuthExpired):
        FileTokenSupplier(tmp_path / "missing")()
    empty = _token(tmp_path, written, body="  \n")
    with pytest.raises(ProviderAuthExpired):
        FileTokenSupplier(empty, now=lambda: datetime(2026, 11, 18, 4, 0, tzinfo=UTC))()


def test_chunk_ranges() -> None:
    d = date(2026, 1, 1)
    assert chunk_ranges(d, date(2026, 1, 1), 100) == [(d, d)]
    r = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    assert r == [
        (date(2026, 1, 1), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 10)),
    ]
    assert chunk_ranges(date(2026, 1, 5), date(2026, 1, 1), 4) == []


def test_previous_day_levels_from_bars() -> None:
    t = datetime(2026, 11, 17, 4, 0, tzinfo=UTC)
    D = Decimal
    bars = [
        Bar(t, t, D("100"), D("105"), D("99"), D("103")),
        Bar(t, t, D("103"), D("104"), D("98"), D("101")),
    ]
    lv = previous_day_levels(bars)
    assert lv is not None and (lv.high, lv.low, lv.close) == (D("105"), D("98"), D("101"))
    assert previous_day_levels([]) is None


def test_worker_registers_the_ingest_job() -> None:
    assert "ingest_tick" in [f.__name__ for f in WorkerSettings.functions]
    assert len(WorkerSettings.cron_jobs) == 1


def test_ingest_is_off_unless_configured() -> None:
    assert ingest_once(Settings(ingest_enabled=False)) == -1
    assert ingest_once(Settings(ingest_enabled=True, ingest_data_source_id="")) == -1


def test_build_provider_demo_and_kite() -> None:
    p, sup = build_provider(Settings(ingest_provider="DEMO"))
    assert isinstance(p, DemoProvider) and sup() == ""
    k, ksup = build_provider(Settings(ingest_provider="KITE", kite_token_file="/nonexistent/.kite_token"))
    assert k.provider_code == "ZERODHA_KITE"
    with pytest.raises(ProviderAuthExpired):
        ksup()
