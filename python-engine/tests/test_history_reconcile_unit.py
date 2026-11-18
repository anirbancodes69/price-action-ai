"""Pure parts of history checks and reconciliation."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from app.ingestion.history_check import HistoryReport, SymbolCoverage, missing_starts
from app.ingestion.reconcile import RECONCILE_WINDOW, reconciliation_due
from app.ingestion.session import session_bar_starts

DAY = date(2026, 11, 18)


def test_missing_starts_against_the_grid() -> None:
    grid = session_bar_starts(DAY, "5m", time(15, 15))
    assert len(grid) == 72  # 09:15 .. 15:10 (Kite grid)
    assert missing_starts(DAY, "5m", set(grid), time(15, 15)) == []
    present = set(grid) - {grid[3], grid[40]}
    assert missing_starts(DAY, "5m", present, time(15, 15)) == [grid[3], grid[40]]
    assert len(missing_starts(DAY, "5m", set(), None)) == 75  # full session without a provider cutoff
    assert len(missing_starts(DAY, "15m", set(), time(15, 15))) == 24


def test_coverage_and_clean_flag() -> None:
    ok = SymbolCoverage("A", 10, 10, (), 0, ())
    bad = SymbolCoverage("B", 10, 8, (date(2026, 1, 5),), 4, ((date(2026, 1, 6), 4),))
    assert ok.coverage_pct == 100.0 and bad.coverage_pct == 80.0
    assert SymbolCoverage("C", 0, 0, (), 0, ()).coverage_pct == 0.0
    assert HistoryReport("5m", None, None, 10, (ok,)).clean
    assert not HistoryReport("5m", None, None, 10, (ok, bad)).clean


def test_reconciliation_window() -> None:
    close = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    sess = (close - timedelta(hours=6, minutes=15), close)
    assert not reconciliation_due(None, close)
    assert not reconciliation_due(sess, close - timedelta(seconds=1))  # session still open
    assert reconciliation_due(sess, close)
    assert reconciliation_due(sess, close + RECONCILE_WINDOW - timedelta(seconds=1))
    assert not reconciliation_due(sess, close + RECONCILE_WINDOW)
