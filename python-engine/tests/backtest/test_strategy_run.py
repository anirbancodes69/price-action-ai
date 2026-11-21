"""Single-strategy run mode (independent backtesting standards §3-§4): isolation proof, 4a / 4b, flags."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.backtest.costs import CostSchedule
from app.backtest.replay import SessionSpec, SymbolData, default_analyse, replay_session
from app.backtest.run import BacktestConfig, SessionInput, run_backtest
from app.backtest.strategy_run import (
    run_strategy_backtest,
    seeded_order,
    strategy_analyse,
    unlimited_profile,
)
from app.domain.analyse import analyse
from app.domain.params import RulesetParams
from app.domain.session import DailyLevels
from app.domain.setups.signal import Signal
from app.domain.setups.types import SetupType
from app.domain.strategies import strategy_detectors
from app.rulesets import load_ruleset

from ..trading._session import CLOSE, OPEN, mk
from ..trading.test_setups_sweep import SAME_BAR

D = Decimal
SID = "liquidity_sweep_reversal"
PREV = DailyLevels(D("1510"), D("1480"), D("1495"))


def _small(code: str = "pa-intraday", version: str = "0.3.0") -> RulesetParams:
    p = load_ruleset(code, version)
    return RulesetParams(
        p.code, p.version, {**p.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5}
    )


def _sym(name: str = "A") -> SymbolData:
    # The 5m bars double as 15m bars: enough history for the snapshot check, the sweep does not read them here.
    rows = mk(SAME_BAR + [("1485", "1487", "1484", "1486")] * 4)
    return SymbolData(name, rows, rows, PREV, D("0.05"))


def _spec() -> SessionSpec:
    return SessionSpec(OPEN.date(), OPEN, CLOSE)


def test_ruleset_0_3_0_differs_from_0_2_0_only_in_the_structure_exit() -> None:
    a, b = load_ruleset("pa-intraday", "0.2.0").values, load_ruleset("pa-intraday", "0.3.0").values
    assert {k for k in a if a[k] != b[k]} == {"exit.structure_exit_enabled"}
    assert set(a) == set(b) and b["exit.structure_exit_enabled"] is False


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown strategy"):
        strategy_detectors("vwap_pullback")


def test_isolation_proof_candidates_equal_the_sweep_only_candidates_of_the_combined_run() -> None:
    """Standards §3: the single-strategy candidates equal the sweep candidates when all detectors run."""
    p = _small()
    b5 = mk(SAME_BAR)
    kw = {"previous_session_open": None, "session_close": CLOSE}
    for k in range(5, len(b5) + 1):
        combined = analyse(b5[:k], b5[:k], OPEN, PREV, p, **kw)  # type: ignore[arg-type]
        alone = analyse(b5[:k], b5[:k], OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **kw)  # type: ignore[arg-type]
        assert alone.setups is not None and combined.setups is not None
        sweep_only = [s for s in combined.setups if s.setup.type is SetupType.LIQUIDITY_SWEEP_REVERSAL]
        assert [(s.setup, s.levels) for s in alone.setups] == [(s.setup, s.levels) for s in sweep_only]
        assert all(s.paqs is None for s in alone.setups)  # no cross-strategy score


def test_isolated_signal_ignores_the_score_gate_and_other_detectors() -> None:
    p = _small()
    b5 = mk(SAME_BAR)
    kw = {"previous_session_open": None, "session_close": CLOSE}
    # The sweep scores below `score.watch_threshold` (non-zone anchors are unscored, OQ-SD-07): the combined run
    # says NO_TRADE / LOW_SCORE, the isolated run takes the candidate.
    combined = analyse(b5, b5, OPEN, PREV, p, **kw)  # type: ignore[arg-type]
    alone = analyse(b5, b5, OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **kw)  # type: ignore[arg-type]
    assert combined.signal is not None and alone.signal is not None
    assert "LOW_SCORE" in combined.signal.reasons or combined.signal.signal is Signal.ENTRY_CONFIRMED
    assert alone.signal.signal is Signal.ENTRY_CONFIRMED
    assert alone.signal.primary is not None
    assert alone.signal.primary.setup.type is SetupType.LIQUIDITY_SWEEP_REVERSAL
    assert alone.signal.reasons == ()


def test_defaults_leave_the_live_analysis_unchanged() -> None:
    p = _small("pa-intraday", "0.2.0")
    b5 = mk(SAME_BAR)
    kw = {"previous_session_open": None, "session_close": CLOSE}
    default = analyse(b5, b5, OPEN, PREV, p, **kw)  # type: ignore[arg-type]
    explicit = analyse(b5, b5, OPEN, PREV, p, detectors=None, isolated=False, **kw)  # type: ignore[arg-type]
    assert default == explicit
    # The live path still runs every detector (here ORB fires as well as the sweep).
    assert default.setups is not None
    assert {s.setup.type for s in default.setups} > {SetupType.LIQUIDITY_SWEEP_REVERSAL}


def test_4a_profile_lifts_every_account_limit_and_keeps_the_fixed_risk_unit() -> None:
    p = load_ruleset("pa-intraday", "0.3.0")
    prof = unlimited_profile(p, D("100000"))
    assert prof.capital * prof.risk_pct / 100 == D("500")  # 0.5% of 1,00,000, unchanged
    assert prof.capital > D("1e9") and prof.max_open_positions > 1000 and prof.max_consecutive_losses > 1000
    assert prof.max_position_value > D("1e9") and prof.daily_loss_limit > D("1e8")
    # Sizing: many open positions do not shrink the next one (no CAPITAL constraint).
    from app.domain.risk.account import AccountState
    from app.domain.risk.sizing import size_position

    busy = AccountState(D("0"), D("0"), D("0"), D("0"), 0, 10, D("99000"))
    sz = size_position(D("1000"), D("995"), prof, busy)
    assert (sz.qty, sz.binding_constraint) == (100, "RISK_BUDGET")  # 500 / 5


def test_seeded_order_is_deterministic_and_not_alphabetical() -> None:
    spec = _spec()
    names = [f"S{i:02d}" for i in range(20)]
    one = sorted(names, key=lambda n: seeded_order(1)(spec, 0, n))
    again = sorted(names, key=lambda n: seeded_order(1)(spec, 0, n))
    two = sorted(names, key=lambda n: seeded_order(2)(spec, 0, n))
    assert one == again and one != names and one != two


def test_4a_and_4b_runs_are_flagged_and_recorded() -> None:
    p = _small()
    inputs = [SessionInput(_spec(), [_sym("A"), _sym("B")])]
    args = (SID, "4a", inputs, p, D("100000"), CostSchedule(), "engine test", "test", "TEST")
    a = run_strategy_backtest(*args)  # type: ignore[arg-type]
    b = run_strategy_backtest(
        SID, "4b", inputs, p, D("100000"), CostSchedule(), "engine test", "test", "TEST"
    )
    for r, exp in ((a, "4a"), (b, "4b")):
        assert (r.record.strategy_id, r.record.experiment) == (SID, exp)
        assert "NOT_ISOLATED" not in r.flags
        assert {"costs_unverified", "UNSUPPORTED_DIRECTION:SHORT"} <= set(r.flags)
    # Only the sweep strategy trades: every trade is the sweep type.
    assert {t.setup_type for t in a.trades} <= {SetupType.LIQUIDITY_SWEEP_REVERSAL.value}
    with pytest.raises(ValueError, match="experiment"):
        run_strategy_backtest(SID, "4c", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")


def test_a_combined_run_is_flagged_not_isolated() -> None:
    p = _small("pa-intraday", "0.2.0")
    cfg = BacktestConfig(p, D("100000"), CostSchedule(), "engine test", "test", "TEST")
    r = run_backtest([SessionInput(_spec(), [_sym("A")])], cfg, default_analyse)
    assert "NOT_ISOLATED" in r.flags and r.record.strategy_id is None


def test_4b_respects_the_slot_limit_where_4a_does_not() -> None:
    """Three symbols give the same candidate on the same bar: 4a trades all, 4b only `max_open_positions` (2)."""
    p = _small()
    inputs = [SessionInput(_spec(), [_sym("A"), _sym("B"), _sym("C")])]
    a = run_strategy_backtest(SID, "4a", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")
    b = run_strategy_backtest(SID, "4b", inputs, p, D("100000"), CostSchedule(), "e", "d", "u")
    assert len(a.trades) == 3
    assert len(b.trades) == 2
    assert any(k.reason == "MAX_POSITIONS_REACHED" for k in b.skips)
    # The two seeds may pick different symbols; the count is the same.
    b2 = run_strategy_backtest(
        SID, "4b", inputs, p, D("100000"), CostSchedule(), "e", "d", "u", tie_break_seed=2
    )
    assert len(b2.trades) == 2


def test_isolated_replay_is_independent_of_other_detectors() -> None:
    """The trade log of the single-strategy replay does not change when other detectors would also fire."""
    p = _small()
    sym = _sym("A")
    prof = unlimited_profile(p, D("100000"))
    one = replay_session([sym], _spec(), p, prof, CostSchedule(), strategy_analyse(SID))
    assert replace(one, spec=one.spec) == one and len(one.trades) == 1
