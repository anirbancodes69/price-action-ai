"""Strict execution path for the original B0 backtest (GAP-1). **Nothing here runs a backtest.**

Pure orchestration: it builds the hash-pinned, review-gated reference data, refuses anything but the original
B0 (`orb_b0`, `pa-intraday 0.6.0`, its released content hash), and runs through the existing loader `b0=` path
and `run_strategy_backtest`. It never falls back to tick 0.05, a 15:30 close or the legacy special-session
list: a missing table, a hash mismatch, an unreviewed table or an unknown value stops the run before any
bar is read. The reference hashes and the resolver version go into the run record.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Connection

from app.backtest.approval import ApprovalError, summarise_approvals, validate_run_approval
from app.backtest.b0_contract import (
    B0_RULESET,
    B0_RULESET_HASH,
    B0_STRATEGY,
    B0ContractError,
    issue_context,
)
from app.backtest.b0_eligibility import B0Reference, Eligibility, PriceBasis
from app.backtest.costs import CostSchedule
from app.backtest.exclusions import Exclusion
from app.backtest.loader import load_backtest_inputs
from app.backtest.reference_tables import (
    ReferenceTableError,
    event_table_from,
    load_price_basis,
    load_table,
    session_table_from,
    tick_table_from,
)
from app.backtest.run import BacktestResult, SessionInput
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import run_strategy_backtest
from app.domain.params import RulesetParams
from app.domain.setups.orb_b0 import detect_orb_b0
from app.domain.strategies import strategy_detectors
from app.domain.ticks import RESOLVER_VERSION
from app.rulesets import ROLE_RESEARCH, load_ruleset, ruleset_role


class B0RunRefused(ValueError):
    """The strict B0 run cannot start; no data was read."""


@dataclass(frozen=True, slots=True)
class TablePin:
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class B0Pins:
    """Every input a B0 run needs, each pinned by SHA-256. All fields are required: there is no default."""

    tick: TablePin
    events: TablePin
    sessions: TablePin
    price_basis_csv: TablePin
    price_basis_manifest: Path


def check_b0_strategy() -> None:
    """The registry must still map `orb_b0` to the B0 detector alone: the existing opening-range detector
    (CUR) or any other detector can never be substituted silently."""
    if tuple(strategy_detectors(B0_STRATEGY)) != (detect_orb_b0,):
        raise B0RunRefused("strategy orb_b0 is not mapped to the B0 detector alone")


def check_b0_ruleset(params: RulesetParams) -> None:
    check_b0_strategy()
    if (params.code, params.version) != B0_RULESET:
        raise B0RunRefused(f"only pa-intraday 0.6.0 is allowed, got {params.code} {params.version}")
    if ruleset_role(params.code, params.version) != ROLE_RESEARCH:
        raise B0RunRefused("the B0 ruleset must have the RESEARCH role")
    if params.content_hash != B0_RULESET_HASH:
        raise B0RunRefused("ruleset content hash differs from the released pa-intraday 0.6.0")


def load_b0_ruleset() -> RulesetParams:
    params = load_ruleset(*B0_RULESET)
    check_b0_ruleset(params)
    return params


def build_reference(pins: B0Pins, *, allow_solo_research: bool = False) -> B0Reference:
    """Load and validate all four tables. Each must be `INDEPENDENTLY_REVIEWED`, or, only with the explicit
    `allow_solo_research=True`, `OWNER_APPROVED_SOLO_RESEARCH` under DEC-045 / DR-12. Statuses are kept per
    table; the run takes the weakest basis (`approval.summarise_approvals`) and, for a solo basis, the exact
    result label. Nothing here waives a hash, schema, provenance or coverage check."""
    try:
        solo = allow_solo_research
        ticks = load_table(pins.tick.path, "tick_table", pins.tick.sha256, allow_solo=solo)
        events = load_table(pins.events.path, "event_table", pins.events.sha256, allow_solo=solo)
        sessions = load_table(pins.sessions.path, "session_table", pins.sessions.sha256, allow_solo=solo)
        basis, basis_t = load_price_basis(
            pins.price_basis_csv.path,
            pins.price_basis_manifest,
            pins.price_basis_csv.sha256,
            allow_solo=solo,
        )
        named = {"tick": ticks, "event": events, "session": sessions, "price_basis": basis_t}
        approvals = {k: t.approval for k, t in named.items()}
        if any(a is None for a in approvals.values()):
            raise ReferenceTableError("a table was loaded without its approval being checked")
        run_approval = summarise_approvals({k: a for k, a in approvals.items() if a is not None})
        hashes = {
            "tick_table_sha256": ticks.sha256,
            "tick_resolver_version": RESOLVER_VERSION,
            "event_table_sha256": events.sha256,
            "session_table_sha256": sessions.sha256,
            "price_basis_sha256": basis_t.sha256,
            "tick_table_version": ticks.version,
            "event_table_version": events.version,
            "session_table_version": sessions.version,
            **{f"{k}_review_status": t.review_status for k, t in named.items()},
            "approval_basis": run_approval.basis,
            "approval_decision_refs": ",".join(run_approval.decision_refs),
            "result_label": run_approval.result_label or "",
        }
        context = issue_context(load_b0_ruleset(), hashes)  # the only production issuer (tested)
        return B0Reference(
            tick_table_from(ticks),
            event_table_from(events),
            session_table_from(sessions),
            {k: PriceBasis(v) for k, v in basis.items()},
            hashes,
            run_approval,
            context,
        )
    except (ReferenceTableError, ApprovalError, B0ContractError, ValueError, KeyError, OSError) as e:
        raise B0RunRefused(f"reference data refused: {e}") from e


@dataclass(frozen=True, slots=True)
class B0Inputs:
    sessions: list[SessionInput]
    exclusions: list[Exclusion]
    eligibility: dict[tuple[str, date], Eligibility]


def load_b0_inputs(
    conn: Connection,
    source: object,
    members: Mapping[str, object],
    first_day: date,
    last_day: date,
    params: RulesetParams,
    reference: B0Reference,
    daily_levels: Mapping[str, Mapping[date, object]] | None = None,
) -> B0Inputs:
    """Sessions for the B0 run via the strict loader path (no legacy list, no previous-day requirement)."""
    check_b0_ruleset(params)
    exclusions: list[Exclusion] = []
    elig: dict[tuple[str, date], Eligibility] = {}
    sessions = load_backtest_inputs(
        conn,
        source,  # type: ignore[arg-type]
        dict(members),  # type: ignore[arg-type]
        first_day,
        last_day,
        params.int_("analysis.lookback_sessions"),
        daily_levels=daily_levels,  # type: ignore[arg-type]
        exclusions=exclusions,
        b0=reference,
        eligibility_out=elig,
    )
    return B0Inputs(sessions, exclusions, elig)


def run_b0(
    inputs: list[SessionInput],
    params: RulesetParams,
    reference: B0Reference,
    experiment: str,
    capital: Decimal,
    engine_version: str,
    data_source: str,
    universe: str,
    slippage: SlippageModel,
    *,
    tie_break_seed: int = 1,
    purpose: str = "EXPLORATION:all",
) -> BacktestResult:
    """Replay the original B0. The ruleset, strategy id and reference hashes are fixed by this function."""
    check_b0_ruleset(params)
    if not reference.hashes.get("tick_table_sha256") or not reference.hashes.get("session_table_sha256"):
        raise B0RunRefused("the run record must carry the table hashes")
    if reference.approval is None or reference.context is None:
        raise B0RunRefused("the approval basis or execution context of the tables is not established")
    try:
        validate_run_approval(reference.approval)
    except ApprovalError as e:
        raise B0RunRefused(f"approval basis inconsistent: {e}") from e
    h = reference.hashes
    if (h.get("approval_basis"), h.get("result_label") or None) != (
        reference.approval.basis,
        reference.approval.result_label,
    ):
        raise B0RunRefused(
            "the run record's approval basis or result label differs from the tables' approval"
        )
    return run_strategy_backtest(
        B0_STRATEGY,
        experiment,
        inputs,
        params,
        capital,
        CostSchedule(),
        engine_version,
        data_source,
        universe,
        tie_break_seed=tie_break_seed,
        purpose=purpose,
        slippage=slippage,
        reference_data=dict(reference.hashes),
        b0_context=reference.context,
    )
