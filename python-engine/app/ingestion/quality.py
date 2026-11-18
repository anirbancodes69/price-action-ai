"""Intraday bar quality checks (ENG-05 §12). Pure functions: no I/O, deterministic.

Issues are returned, never silently fixed. Rejected bars are excluded from ``accepted``.
LATE_BAR is a fetch-time concern (per-bar deadline) and lives in the fetcher, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.ingestion.session import bar_minutes, session_bar_starts, session_bounds
from app.providers.base import ProviderBar, Timeframe

# HYPOTHESIS: 15m vs sum-of-5m volume tolerance, to be calibrated on real Kite data (OQ-INT-01).
VOLUME_TOLERANCE = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class QualityIssue:
    type: str  # MISSING_BAR, MISALIGNED_BAR, OUTSIDE_SESSION, INVALID_OHLC, DUPLICATE, AGGREGATE_MISMATCH
    bar_start: datetime | None
    detail: str


@dataclass(frozen=True, slots=True)
class BarCheckResult:
    accepted: list[ProviderBar]
    issues: list[QualityIssue]

    @property
    def complete(self) -> bool:
        return not any(i.type == "MISSING_BAR" for i in self.issues)


def _valid_ohlc(b: ProviderBar) -> bool:
    return (
        min(b.open, b.high, b.low, b.close) > 0
        and b.low <= min(b.open, b.close)
        and b.high >= max(b.open, b.close)
        and b.volume >= 0
    )


def check_session_bars(
    day: date,
    timeframe: Timeframe,
    bars: list[ProviderBar],
    expected: list[datetime] | None = None,
) -> BarCheckResult:
    """Validate one instrument's bars for one session.

    ``expected`` overrides the normal grid for special sessions (from ``market_calendar``).
    Duplicates keep the last bar received, plus a DUPLICATE issue.
    """
    grid = expected if expected is not None else session_bar_starts(day, timeframe)
    open_, close = session_bounds(day)
    step = bar_minutes(timeframe)
    issues: list[QualityIssue] = []
    kept: dict[datetime, ProviderBar] = {}
    for b in bars:
        ts = b.bar_start
        if ts.tzinfo is None:
            issues.append(QualityIssue("MISALIGNED_BAR", ts, "naive timestamp"))
        elif not (open_ <= ts < close):
            issues.append(QualityIssue("OUTSIDE_SESSION", ts, "outside regular session"))
        elif (ts - open_).total_seconds() % (step * 60) != 0:
            issues.append(QualityIssue("MISALIGNED_BAR", ts, f"not on the {timeframe} grid"))
        elif not _valid_ohlc(b):
            issues.append(QualityIssue("INVALID_OHLC", ts, "OHLC invalid"))
        else:
            if ts in kept:
                issues.append(QualityIssue("DUPLICATE", ts, "later bar replaces earlier"))
            kept[ts] = b
    issues += [QualityIssue("MISSING_BAR", ts, "no bar received") for ts in grid if ts not in kept]
    return BarCheckResult([kept[k] for k in sorted(kept)], issues)


def check_aggregate(five: list[ProviderBar], fifteen: list[ProviderBar]) -> list[QualityIssue]:
    """Each 15m bar must equal its three 5m bars: OHLC exactly, volume within tolerance.

    A group missing any 5m bar is skipped (already a MISSING_BAR). The provider's 15m bar is kept.
    """
    by_start = {b.bar_start: b for b in five}
    step = bar_minutes("5m")
    issues: list[QualityIssue] = []
    for f in fifteen:
        parts = [
            by_start.get(
                f.bar_start.fromtimestamp(f.bar_start.timestamp() + i * step * 60, f.bar_start.tzinfo)
            )
            for i in range(bar_minutes("15m") // step)
        ]
        if any(p is None for p in parts):
            continue
        g = [p for p in parts if p is not None]
        exp = (g[0].open, max(p.high for p in g), min(p.low for p in g), g[-1].close)
        vol = sum(p.volume for p in g)
        ohlc_ok = (f.open, f.high, f.low, f.close) == exp
        vol_ok = abs(f.volume - vol) <= VOLUME_TOLERANCE * max(vol, 1)
        if not (ohlc_ok and vol_ok):
            issues.append(QualityIssue("AGGREGATE_MISMATCH", f.bar_start, "15m differs from its 5m bars"))
    return issues
