"""Backtest orchestration, reproducibility record and flags (TRD-06 §2 BT-05, §3, §11)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

from app.backtest.b0_contract import (
    B0_STRATEGY,
    B0ContractError,
    B0ExecutionContext,
    is_b0_related,
    validate_b0_config,
)
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
from app.backtest.slippage import SlippageModel
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
    # D-4: `None` = the legacy stop-only model at `backtest.slippage_pct`, so earlier runs reproduce exactly.
    slippage: SlippageModel | None = None
    # B0 research path (OD-8 Step 2): hash-pinned reference data used by the run, for example
    # tick_table_sha256, tick_resolver_version, session_table_sha256, event_table_sha256.
    reference_data: Mapping[str, str] = field(default_factory=dict)

    # B0 only: the validated execution context issued by the strict runner (`b0_contract.issue_context`).
    b0_context: B0ExecutionContext | None = None

    def __post_init__(self) -> None:
        """`orb_b0` and ruleset 0.6.0 need the strict runner's context and evidence (b0_contract). For B0 the
        reference data is copied into a read-only mapping so it cannot change after validation."""
        validate_b0_config(self.params, self.strategy_id, self.reference_data, self.b0_context)
        if is_b0_related(self.params, self.strategy_id):
            object.__setattr__(self, "reference_data", MappingProxyType(dict(self.reference_data)))

    @property
    def slippage_model(self) -> SlippageModel:
        return self.slippage or SlippageModel.legacy(self.params.decimal("backtest.slippage_pct"))


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
    ruleset_hash: str = ""  # SHA-256 of the exact ruleset values (identifies configuration differences)
    slippage: dict[str, str] = field(default_factory=dict)  # the assumed model (D-4); never measured
    reference_data: dict[str, str] = field(
        default_factory=dict
    )  # table hashes and resolver version (B0 path)
    run_digest: str = ""  # B0 only: binds this record's identity fields (see `compute_run_digest`)


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
    if getattr(analyse_fn, "strategy_id", None) == B0_STRATEGY and cfg.strategy_id != B0_STRATEGY:
        raise B0ContractError("the B0 analysis step cannot run under a configuration of another strategy")
    ordered = sorted(sessions, key=lambda s: s.spec.session_date)
    results: list[SessionResult] = []
    equity = cfg.capital
    for s in ordered:
        capital = equity if cfg.sizing_mode == "COMPOUNDING" else cfg.capital
        profile = cfg.profile_fn(cfg.params, capital)
        r = replay_session(
            s.symbols,
            s.spec,
            cfg.params,
            profile,
            cfg.schedule,
            analyse_fn,
            cfg.order_key,
            slippage=cfg.slippage_model,
        )
        results.append(r)
        equity += r.net_pnl
    return assemble_result(results, cfg, inputs_hash(ordered))


def compute_run_digest(rec: RunRecord) -> str:
    """SHA-256 over the identity of a run: strategy, experiment, ruleset hash, input hash, reference data
    (hashes, statuses, label), slippage, costs, engine, universe, data source, purpose and the session span.
    B0 evidence carries it, so evidence from one run cannot be attached to another run's result."""
    body = {
        "strategy_id": rec.strategy_id, "experiment": rec.experiment, "ruleset": rec.ruleset,
        "ruleset_hash": rec.ruleset_hash, "inputs_hash": rec.inputs_hash,
        "reference_data": dict(rec.reference_data), "slippage": dict(rec.slippage),
        "cost_schedule_version": rec.cost_schedule_version, "engine_version": rec.engine_version,
        "universe": rec.universe, "data_source": rec.data_source, "purpose": rec.purpose,
        "sizing_mode": rec.sizing_mode, "first_session": str(rec.first_session),
        "last_session": str(rec.last_session), "sessions": rec.sessions,
    }  # fmt: skip
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


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
        cfg.params.content_hash,
        cfg.slippage_model.to_dict(),
        dict(cfg.reference_data),
    )
    if is_b0_related(cfg.params, cfg.strategy_id):
        record = replace(record, run_digest=compute_run_digest(record))
    return BacktestResult(record, tuple(results), metrics, tuple(curve), tuple(flags))
