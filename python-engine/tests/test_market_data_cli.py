"""The owner CLI's argument rules (scripts/market_data_cli.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "market_data_cli.py"


@pytest.fixture(scope="module")
def cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("market_data_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_accepts_the_daily_timeframe_for_the_chart_context(cli: ModuleType) -> None:
    args = cli._parser().parse_args(
        ["backfill", "--timeframe", "1D", "--from", "2026-01-01", "--to", "2026-11-19"]
    )
    assert (args.cmd, args.timeframe) == ("backfill", "1D")


def test_backfill_still_defaults_to_5m_and_accepts_15m(cli: ModuleType) -> None:
    base = ["backfill", "--from", "2026-09-01", "--to", "2026-11-19"]
    assert cli._parser().parse_args(base).timeframe == "5m"
    assert cli._parser().parse_args([*base, "--timeframe", "15m"]).timeframe == "15m"


def test_backfill_resumes_by_default_and_can_reach_older_history(cli: ModuleType) -> None:
    base = ["backfill", "--from", "2026-01-01", "--to", "2026-08-31"]
    a = cli._parser().parse_args(base)
    assert (a.no_resume, a.as_of) == (False, None)
    b = cli._parser().parse_args([*base, "--no-resume", "--as-of", "2026-11-19"])
    assert (b.no_resume, str(b.as_of)) == (True, "2026-11-19")


def test_history_check_has_no_daily_grid(cli: ModuleType) -> None:
    with pytest.raises(SystemExit):
        cli._parser().parse_args(
            ["history-check", "--timeframe", "1D", "--from", "2026-01-01", "--to", "2026-11-19"]
        )
