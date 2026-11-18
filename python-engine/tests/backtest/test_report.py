"""Report formatting (TRD-06 BT-06, §10, §11)."""

from __future__ import annotations

import json
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.report import DISCLAIMER, UNVERIFIED_COSTS, format_report, report_dict
from app.backtest.run import BacktestConfig, SessionInput, run_backtest

from .test_metrics_splits_run import cfg, two_sessions
from .test_replay import make_analyse

D = Decimal


def _result():  # type: ignore[no-untyped-def]
    return run_backtest(two_sessions(), cfg(), make_analyse({("A", 2): 80}))


def test_text_report_carries_disclaimers_flags_and_numbers() -> None:
    text = format_report(_result())
    assert DISCLAIMER in text and UNVERIFIED_COSTS in text
    assert "LOW SAMPLE" in text and "short_history" in text and "survivorship_bias_risk" in text
    assert "Trades 2" in text and "TARGET 2" in text
    assert "OPENING_RANGE_BREAKOUT" in text and "pa-intraday 0.1.0" in text


def test_text_report_handles_no_trades() -> None:
    empty = run_backtest(two_sessions(), cfg(), make_analyse({}))
    text = format_report(empty)
    assert "Trades 0" in text and "n/a" in text and "Exit mix: none" in text


def test_report_dict_is_json_serialisable_and_exact() -> None:
    r = _result()
    d = report_dict(r)
    json.dumps(d)  # Decimals, datetimes and dataclasses all converted
    assert d["disclaimer"] == DISCLAIMER and d["record"]["sessions"] == 2
    assert len(d["trades"]) == 2 and d["trades"][0]["qty"] == 476
    assert d["trades"][0]["net_pnl"] == str(r.trades[0].net_pnl)
    assert d["metrics"]["trades"] == 2 and len(d["equity_curve"]) == 2
    assert (
        BacktestConfig is not None and SessionInput is not None and CostSchedule is not None and D is not None
    )
