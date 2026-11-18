"""Bar-close fetcher (ENG-05 §12 steps 1-2, ARC-05 §3).

At each bar close (+ settle delay) fetch the just-completed bar for every instrument, run the
quality checks, and hand accepted bars to a ``BarStore``. Forming bars are never requested or stored.
Persistence to Postgres (ingestion runs, candles, ``data_quality_issues``) is a ``BarStore``
implementation added with the DB writer; this module has no I/O besides the provider.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Protocol

from app.ingestion.quality import QualityIssue, check_session_bars
from app.ingestion.session import bar_minutes
from app.providers.base import (
    MarketDataProvider,
    ProviderAuthExpired,
    ProviderBar,
    ProviderContext,
    ProviderError,
    ProviderInstrumentRef,
    Timeframe,
)

# HYPOTHESES (ENG-05 §12 / §5): to calibrate on real provider behaviour.
SETTLE_DELAY_S = 20.0
POLL_INTERVAL_S = 15.0

RunStatus = Literal["COMPLETED", "PARTIAL", "FAILED"]


class BarStore(Protocol):
    def save(self, symbol: str, timeframe: Timeframe, bars: list[ProviderBar]) -> None: ...


class InMemoryBarStore:
    """Test/dev store. Upsert by ``bar_start`` (idempotent reruns)."""

    def __init__(self) -> None:
        self.bars: dict[tuple[str, str], dict[datetime, ProviderBar]] = {}

    def save(self, symbol: str, timeframe: Timeframe, bars: list[ProviderBar]) -> None:
        slot = self.bars.setdefault((symbol, timeframe), {})
        for b in bars:
            slot[b.bar_start] = b


@dataclass(slots=True)
class InstrumentOutcome:
    symbol: str
    stored: bool
    issues: list[QualityIssue] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class FetchReport:
    timeframe: Timeframe
    bar_start: datetime
    status: RunStatus
    outcomes: list[InstrumentOutcome]
    error_code: str | None = None

    @property
    def issues(self) -> list[QualityIssue]:
        return [i for o in self.outcomes for i in o.issues]


def run_bar_close(
    provider: MarketDataProvider,
    ctx: ProviderContext,
    store: BarStore,
    instruments: Sequence[ProviderInstrumentRef],
    timeframe: Timeframe,
    bar_start: datetime,
    now: Callable[[], datetime],
    sleep: Callable[[float], None] = time.sleep,
    settle_s: float = SETTLE_DELAY_S,
    poll_s: float = POLL_INTERVAL_S,
) -> FetchReport:
    """Fetch the bar that started at ``bar_start`` for all instruments.

    Waits ``settle_s`` after the close, then polls each missing bar until the next bar close, after
    which it is reported as ``LATE_BAR`` (the session-end reconciliation backfills it).
    Raises ``ValueError`` if the bar has not closed yet (no forming bars).
    """
    step = timedelta(minutes=bar_minutes(timeframe))
    close = bar_start + step
    if now() < close:
        raise ValueError("bar has not closed yet")
    deadline = close + step
    sleep(settle_s)

    outcomes: list[InstrumentOutcome] = []
    for ref in instruments:
        outcome = InstrumentOutcome(ref.symbol, stored=False)
        outcomes.append(outcome)
        try:
            bar = _fetch_one(provider, ctx, ref, timeframe, bar_start, close, deadline, now, sleep, poll_s)
        except ProviderAuthExpired:
            return FetchReport(timeframe, bar_start, "FAILED", outcomes, "PROVIDER_AUTH_EXPIRED")
        except ProviderError as exc:
            outcome.error = type(exc).__name__
            continue
        if bar is None:
            outcome.issues.append(QualityIssue("LATE_BAR", bar_start, "not available by the deadline"))
            continue
        result = check_session_bars(bar_start.date(), timeframe, [bar], expected=[bar_start])
        outcome.issues = result.issues
        if result.accepted:
            store.save(ref.symbol, timeframe, result.accepted)
            outcome.stored = True

    failed = sum(1 for o in outcomes if not o.stored)
    if failed == 0:
        status: RunStatus = "COMPLETED"
    elif failed == len(outcomes):
        status = "FAILED"
    else:
        status = "PARTIAL"
    return FetchReport(timeframe, bar_start, status, outcomes)


def _fetch_one(
    provider: MarketDataProvider,
    ctx: ProviderContext,
    ref: ProviderInstrumentRef,
    timeframe: Timeframe,
    bar_start: datetime,
    close: datetime,
    deadline: datetime,
    now: Callable[[], datetime],
    sleep: Callable[[float], None],
    poll_s: float,
) -> ProviderBar | None:
    while True:
        bars = provider.fetch_bars(ctx, ref, timeframe, bar_start, close)
        for b in bars:
            if b.bar_start == bar_start:
                return b
        if now() >= deadline:
            return None
        sleep(poll_s)
