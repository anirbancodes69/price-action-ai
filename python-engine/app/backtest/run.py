"""Backtest orchestration, reproducibility record and flags (TRD-06 §2 BT-05, §3, §11)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from app.backtest.costs import CostSchedule
from app.backtest.metrics import Metrics, compute_metrics, equity_curve
from app.backtest.replay import (
    AnalyseFn,
    OrderKey,
    SessionResult,
    SessionSpec,
    Skip,
    SymbolData,
    default_analyse,
    replay_session,
    score_then_symbol,
)
from app.backtest.trade import Trade
from app.domain.candles import candles_hash
from app.domain.params import RulesetParams
from app.domain.risk.account import RiskProfile

MIN_SESSIONS = 120  # TRD-06 §3 minimum test span


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    params: RulesetParams
    capital: Decimal
    schedule: CostSchedule
    engine_version: str
    data_source: str
    universe: str
    sizing_mode: Literal["FIXED", "COMPOUNDING"] = "FIXED"
    point_in_time_universe: bool = False
    purpose: str = "EXPLORATION"
    # Single-strategy run mode (standards §3). `None` is a combined run, flagged `NOT_ISOLATED`.
    strategy_id: str | None = None
    experiment: str | None = None  # "4a" or "4b" (standards §4)
    profile_fn: Callable[[RulesetParams, Decimal], RiskProfile] = RiskProfile.from_params
    order_key: OrderKey = score_then_symbol


@dataclass(frozen=True, slots=True)
class SessionInput:
    spec: SessionSpec
    symbols: Sequence[SymbolData]


@dataclass(frozen=True, slots=True)
class RunRecord:
    """What is needed to reproduce the run (BT-05)."""

    ruleset: str
    engine_version: str
    cost_schedule_version: str
    universe: str
    data_source: str
    timeframes: tuple[str, ...]
    sizing_mode: str
    purpose: str
    inputs_hash: str
    first_session: date | None
    last_session: date | None
    sessions: int
    strategy_id: str | None = None
    experiment: str | None = None


@dataclass(frozen=True, slots=True)
class BacktestResult:
    record: RunRecord
    sessions: tuple[SessionResult, ...]
    metrics: Metrics
    equity_curve: tuple[tuple[date, Decimal], ...]  # end-of-session equity
    flags: tuple[str, ...]

    @property
    def trades(self) -> tuple[Trade, ...]:
        return tuple(t for s in self.sessions for t in s.trades)

    @property
    def skips(self) -> tuple[Skip, ...]:
        return tuple(k for s in self.sessions for k in s.skips)


def inputs_hash(sessions: Sequence[SessionInput]) -> str:
    h = hashlib.sha256()
    for s in sessions:
        h.update(s.spec.session_date.isoformat().encode())
        for sym in sorted(s.symbols, key=lambda x: x.symbol):
            h.update(sym.symbol.encode())
            h.update(candles_hash(sym.bars_5m).encode())
            h.update(candles_hash(sym.bars_15m).encode())
    return h.hexdigest()


def run_backtest(
    sessions: Sequence[SessionInput],
    cfg: BacktestConfig,
    analyse_fn: AnalyseFn = default_analyse,
) -> BacktestResult:
    """Replay each session in date order. Account limits reset every session (TRD-05 §8)."""
    ordered = sorted(sessions, key=lambda s: s.spec.session_date)
    results: list[SessionResult] = []
    equity = cfg.capital
    for s in ordered:
        capital = equity if cfg.sizing_mode == "COMPOUNDING" else cfg.capital
        profile = cfg.profile_fn(cfg.params, capital)
        r = replay_session(s.symbols, s.spec, cfg.params, profile, cfg.schedule, analyse_fn, cfg.order_key)
        results.append(r)
        equity += r.net_pnl
    return assemble_result(results, cfg, inputs_hash(ordered))


def assemble_result(results: Sequence[SessionResult], cfg: BacktestConfig, input_hash: str) -> BacktestResult:
    """Metrics, curve, flags and run record for replayed sessions (also used to merge chunks)."""
    metrics = compute_metrics(results, cfg.capital)
    curve: list[tuple[date, Decimal]] = []
    values = equity_curve(results, cfg.capital)[1:]
    for r, v in zip(results, values, strict=True):
        curve.append((r.spec.session_date, v))
    flags: list[str] = []
    if len(results) < MIN_SESSIONS:
        flags.append("short_history")
    if not cfg.point_in_time_universe:
        flags.append("survivorship_bias_risk")
    if metrics.low_sample:
        flags.append("low_sample")
    if metrics.end_of_data_trades:
        flags.append("end_of_data_trades")
    if cfg.strategy_id is None:
        flags.append("NOT_ISOLATED")
    else:
        flags.append("costs_unverified")  # OQ-BT-02, until the owner verifies the schedule (D-6)
        flags.append("UNSUPPORTED_DIRECTION:SHORT")
    record = RunRecord(
        f"{cfg.params.code} {cfg.params.version}",
        cfg.engine_version,
        cfg.schedule.version,
        cfg.universe,
        cfg.data_source,
        ("5m", "15m"),
        cfg.sizing_mode,
        cfg.purpose,
        input_hash,
        results[0].spec.session_date if results else None,
        results[-1].spec.session_date if results else None,
        len(results),
        cfg.strategy_id,
        cfg.experiment,
    )
    return BacktestResult(record, tuple(results), metrics, tuple(curve), tuple(flags))
