"""Single-strategy run mode (independent backtesting standards §3-§4, ADR-018).

Builds the pieces `run_backtest` needs to replay exactly one strategy:

* `strategy_analyse`: only the strategy's detector runs, the candidate is taken directly (no PAQS, no score
  gate, no cross-strategy selection). The 15m context filter and the structure exit are the strategy's own
  rules (see its page and ruleset), so nothing else is applied.
* Experiment 4a: every valid candidate is a trade; no position, open-risk, daily-loss, streak or value limits.
  The size is a fixed risk unit (`risk.default_risk_per_trade_pct` of the capital). One open trade per
  symbol (the replay's `ALREADY_IN_POSITION`).
* Experiment 4b: the project's account limits (TRD-05) with a documented, deterministic tie-break: candidates
  closing on the same bar compete in order of `sha256(seed | session date | symbol)`. A second seed re-runs
  it to show how much the order matters. Alphabetical order is never used.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.replay import AnalyseFn, OrderKey, SessionSpec, SymbolData
from app.backtest.run import BacktestConfig, BacktestResult, SessionInput, run_backtest
from app.backtest.slippage import SlippageModel
from app.domain.analyse import AnalysisResult, analyse
from app.domain.params import RulesetParams
from app.domain.risk.account import RiskProfile
from app.domain.strategies import strategy_detectors

UNLIMITED = Decimal(10) ** 12
UNLIMITED_COUNT = 10**6


def strategy_analyse(strategy_id: str) -> AnalyseFn:
    """The replay's analysis step for one strategy (BT-01: only bars closed by the signal bar)."""
    detectors = strategy_detectors(strategy_id)

    def run(sym: SymbolData, k: int, spec: SessionSpec, params: RulesetParams) -> AnalysisResult:
        bars5 = list(sym.bars_5m[:k])
        bars15 = [b for b in sym.bars_15m if b.end <= bars5[-1].end]
        return analyse(
            bars5,
            bars15,
            spec.session_open,
            sym.prev_day,
            params,
            spec.previous_session_open,
            sym.tick,
            spec.session_close,
            sym.zone_cache,
            detectors=detectors,
            isolated=True,
        )

    return run


def unlimited_profile(params: RulesetParams, capital: Decimal) -> RiskProfile:
    """Experiment 4a: only the fixed risk per trade stays; every account and capital limit is lifted.

    The size has a `CAPITAL` term (capital minus the open positions' cost), so the capital itself is made
    unlimited and `risk_pct` is scaled so that the risk budget per trade is unchanged (₹500 on ₹1,00,000).
    """
    budget = capital * params.decimal("risk.default_risk_per_trade_pct") / 100
    return RiskProfile(
        capital=UNLIMITED,
        risk_pct=budget / UNLIMITED * 100,
        max_position_value=UNLIMITED,
        daily_loss_limit_pct=Decimal(10**6),
        max_consecutive_losses=UNLIMITED_COUNT,
        max_open_positions=UNLIMITED_COUNT,
        max_open_risk_pct=Decimal(10**6),
    )


def seeded_order(seed: int) -> OrderKey:
    """Experiment 4b tie-break: a deterministic pseudo-random order per (seed, session, symbol)."""

    def key(spec: SessionSpec, _paqs: int, symbol: str) -> str:
        return hashlib.sha256(f"{seed}|{spec.session_date.isoformat()}|{symbol}".encode()).hexdigest()

    return key


def strategy_config(
    strategy_id: str,
    experiment: str,
    params: RulesetParams,
    capital: Decimal,
    schedule: CostSchedule,
    engine_version: str,
    data_source: str,
    universe: str,
    *,
    tie_break_seed: int = 1,
    purpose: str = "EXPLORATION",
    slippage: SlippageModel | None = None,
) -> BacktestConfig:
    if experiment not in ("4a", "4b"):
        raise ValueError("experiment must be '4a' or '4b'")
    return BacktestConfig(
        params,
        capital,
        schedule,
        engine_version,
        data_source,
        universe,
        purpose=purpose,
        strategy_id=strategy_id,
        experiment=experiment,
        profile_fn=unlimited_profile if experiment == "4a" else RiskProfile.from_params,
        order_key=seeded_order(tie_break_seed),
        slippage=slippage,
    )


def run_strategy_backtest(
    strategy_id: str,
    experiment: str,
    sessions: list[SessionInput],
    params: RulesetParams,
    capital: Decimal,
    schedule: CostSchedule,
    engine_version: str,
    data_source: str,
    universe: str,
    *,
    tie_break_seed: int = 1,
    purpose: str = "EXPLORATION",
    slippage: SlippageModel | None = None,
) -> BacktestResult:
    cfg = strategy_config(
        strategy_id,
        experiment,
        params,
        capital,
        schedule,
        engine_version,
        data_source,
        universe,
        tie_break_seed=tie_break_seed,
        purpose=purpose,
        slippage=slippage,
    )
    return run_backtest(sessions, cfg, strategy_analyse(strategy_id))
