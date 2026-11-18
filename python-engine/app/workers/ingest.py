"""arq job: ingest due bars once a minute (ENG-05 §12). The calendar decides whether anything is due."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

from app.ingestion.reconcile import run_maintenance
from app.ingestion.repository import IngestionRepository
from app.ingestion.schedule import run_due_bars
from app.ingestion.session import IST
from app.ingestion.universe import universe_refs
from app.providers.base import MarketDataProvider, ProviderAuthExpired, ProviderContext
from app.providers.demo import DemoProvider
from app.providers.kite.provider import KiteProvider
from app.providers.kite.token import FileTokenSupplier
from app.settings import Settings, get_settings

log = logging.getLogger(__name__)


def build_provider(s: Settings) -> tuple[MarketDataProvider, Callable[[], str]]:
    """Provider and its just-in-time credential supplier for the configured source."""
    if s.ingest_provider == "DEMO":
        return DemoProvider(), lambda: ""
    return KiteProvider(s.kite_api_key.get_secret_value()), FileTokenSupplier(Path(s.kite_token_file))


def ingest_once(
    s: Settings,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """One tick. Returns the number of bar-close reports produced; `-1` when ingestion cannot run."""
    if not s.ingest_enabled or not s.ingest_data_source_id:
        return -1
    source = uuid.UUID(s.ingest_data_source_id)
    provider, supplier = build_provider(s)
    engine = create_engine(s.database_url.get_secret_value())
    try:
        with engine.connect() as conn:
            refs = universe_refs(
                conn, s.ingest_universe_code, provider.provider_code, now().astimezone(IST).date()
            )
            if not refs:
                log.warning("ingest_no_universe_refs", extra={"universe": s.ingest_universe_code})
                return -1
            ctx = ProviderContext(str(source), supplier)
            try:
                reports = run_due_bars(conn, source, provider, ctx, refs, now, sleep)
            except ProviderAuthExpired:
                log.warning("ingest_auth_expired")  # the owner must run scripts/kite_login.py
                return -1
            ids = IngestionRepository(conn, source, provider.provider_code).resolve_instruments(refs, now())
            conn.rollback()
            stale, rec = run_maintenance(conn, source, provider, ctx, refs, ids, now(), sleep)
            if stale:
                log.warning("ingest_stale_runs_recovered", extra={"count": stale})
            if rec is not None:
                log.info(
                    "ingest_reconciled",
                    extra={"day": str(rec.day), "gaps_before": rec.gaps_before, "gaps_after": rec.gaps_after},
                )
            return len(reports)
    finally:
        engine.dispose()


async def ingest_tick(ctx: dict[str, Any]) -> int:
    n = await asyncio.to_thread(ingest_once, get_settings())
    if n > 0:
        log.info("ingest_tick", extra={"reports": n})
    return n
