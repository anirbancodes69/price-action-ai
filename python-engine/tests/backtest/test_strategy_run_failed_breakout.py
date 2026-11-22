"""Strategy 02 in the single-strategy run mode: isolation proof, 4a / 4b, flags (standards §3-§5)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.backtest.costs import CostSchedule
from app.backtest.replay import SymbolData
from app.backtest.run import SessionInput
from app.backtest.strategy_run import run_strategy_backtest
from app.domain.analyse import analyse
from app.domain.params import RulesetParams
from app.domain.session import DailyLevels
from app.domain.setups.signal import Signal
from app.domain.setups.types import SetupType
from app.domain.strategies import strategy_detectors
from app.rulesets import load_ruleset

from ..trading._session import CLOSE, OPEN, mk
from ..trading.test_setups_failed_breakdown import SEQ
from .test_strategy_run import _spec

D = Decimal
SID = "failed_breakout"
PREV = DailyLevels(D("1510"), D("1480"), D("1495"))
# After the confirmation bar the price rises to the PDH target 1510, so the entry (open of bar 8) fills and exits.
TAIL = [
    ("1482.5", "1492", "1482", "1491"),
    ("1491", "1512", "1490", "1511"),
    ("1511", "1512", "1508", "1510"),
]


def _small() -> RulesetParams:
    p = load_ruleset("pa-intraday", "0.4.0")
    return RulesetParams(
        p.code, p.version, {**p.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5}
    )


def _sym(name: str = "A") -> SymbolData:
    rows = mk([*SEQ, *TAIL])
    return SymbolData(name, rows, rows, PREV, D("0.05"))


def test_ruleset_0_4_0_differs_from_0_3_0_only_in_the_two_new_parameters() -> None:
    a, b = load_ruleset("pa-intraday", "0.3.0").values, load_ruleset("pa-intraday", "0.4.0").values
    assert set(b) - set(a) == {"setup.failed_breakout_enabled", "setup.failed_break_max_bars"}
    assert {k for k in a if a[k] != b[k]} == set()
    assert b["setup.failed_breakout_enabled"] is True and b["setup.failed_break_max_bars"] == 6


def test_isolation_proof_candidates_equal_the_failed_breakdown_only_candidates_of_the_combined_run() -> None:
    p = _small()
    b5 = mk(SEQ)
    kw = {"previous_session_open": None, "session_close": CLOSE}
    for k in range(5, len(b5) + 1):
        combined = analyse(b5[:k], b5[:k], OPEN, PREV, p, **kw)  # type: ignore[arg-type]
        alone = analyse(b5[:k], b5[:k], OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **kw)  # type: ignore[arg-type]
        assert alone.setups is not None and combined.setups is not None
        own = [s for s in combined.setups if s.setup.type is SetupType.FAILED_BREAKDOWN_RECLAIM]
        assert [(s.setup, s.levels) for s in alone.setups] == [(s.setup, s.levels) for s in own]
        assert all(s.paqs is None for s in alone.setups)


def test_isolated_signal_takes_the_candidate_without_the_score_gate() -> None:
    p = _small()
    b5 = mk(SEQ)
    kw = {"previous_session_open": None, "session_close": CLOSE}
    alone = analyse(b5, b5, OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **kw)  # type: ignore[arg-type]
    assert alone.signal is not None and alone.signal.primary is not None
    assert alone.signal.signal is Signal.ENTRY_CONFIRMED
    assert alone.signal.primary.setup.type is SetupType.FAILED_BREAKDOWN_RECLAIM
    assert alone.signal.reasons == ()


def test_4a_and_4b_runs_are_flagged_recorded_and_trade_only_this_strategy() -> None:
    p = _small()
    inputs = [SessionInput(_spec(), [_sym("A"), _sym("B")])]
    a = run_strategy_backtest(SID, "4a", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")
    b = run_strategy_backtest(SID, "4b", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")
    for r, exp in ((a, "4a"), (b, "4b")):
        assert (r.record.strategy_id, r.record.experiment) == (SID, exp)
        assert "NOT_ISOLATED" not in r.flags
        assert {"costs_unverified", "UNSUPPORTED_DIRECTION:SHORT"} <= set(r.flags)
    assert len(a.trades) == 2
    assert {t.setup_type for t in a.trades} == {SetupType.FAILED_BREAKDOWN_RECLAIM.value}
    assert {t.anchor for t in a.trades} == {"PDL"} and {t.swept_level for t in a.trades} == {D("1480")}


def test_4b_respects_the_slot_limit_where_4a_does_not() -> None:
    p = _small()
    inputs = [SessionInput(_spec(), [_sym("A"), _sym("B"), _sym("C")])]
    a = run_strategy_backtest(SID, "4a", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")
    b = run_strategy_backtest(SID, "4b", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")
    assert len(a.trades) == 3 and len(b.trades) == 2
    assert any(k.reason == "MAX_POSITIONS_REACHED" for k in b.skips)


def test_unknown_strategy_is_still_rejected() -> None:
    with pytest.raises(ValueError, match="unknown strategy"):
        strategy_detectors("failed_breakdown")
