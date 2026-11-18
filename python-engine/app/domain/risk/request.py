"""Risk calculation for a plan: limits, validation, sizing (TRD-05 §1, §8, §11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.params import RulesetParams
from app.domain.risk.account import AccountState, RiskProfile, check_account_limits
from app.domain.risk.rounding import down_to_tick, entry_up, inr
from app.domain.risk.sizing import Sizing, size_position
from app.domain.risk.validation import (
    effective_min_rr,
    risk_reward,
    stop_override_warning,
    validate_rr,
    validate_stop,
)
from app.domain.setups.types import SetupDirection

MIN_CAPITAL = Decimal(10_000)  # TRD-05 §9


@dataclass(frozen=True, slots=True)
class RiskRequest:
    direction: SetupDirection
    entry: Decimal
    stop: Decimal
    target: Decimal
    tick_size: Decimal
    lot_size: int
    profile: RiskProfile
    state: AccountState
    session_open: bool
    bar_end: datetime
    cutoff: datetime
    user_min_rr: Decimal | None = None
    engine_stop: Decimal | None = None  # structural stop, when the user edited the plan


@dataclass(frozen=True, slots=True)
class RiskResult:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    blocked_reason: str | None
    entry: Decimal | None = None
    stop: Decimal | None = None
    target: Decimal | None = None
    rr: Decimal | None = None
    sizing: Sizing | None = None
    remaining_daily_loss: Decimal | None = None
    levels_overridden: bool = False
    ruleset_version: str = ""
    # TRD-05 §10/§11: cost estimates need the unverified TRD-06 §5 schedule, so they are not computed yet.
    est_round_trip_costs: Decimal | None = field(default=None)
    rr_after_costs: Decimal | None = field(default=None)


def calculate_risk(req: RiskRequest, params: RulesetParams) -> RiskResult:
    """Order: direction, capital, account limits (RM-07), rounding, stop, R:R, sizing."""
    ver = f"{params.code} {params.version}"

    def fail(*errors: str, blocked: str | None = None) -> RiskResult:
        return RiskResult(False, errors, (), blocked, ruleset_version=ver)

    if req.direction is not SetupDirection.LONG:
        return fail("SHORT_NOT_SUPPORTED")
    if req.profile.capital < MIN_CAPITAL:
        return fail("CAPITAL_BELOW_MINIMUM")
    blocked = check_account_limits(req.state, req.profile, req.session_open, req.bar_end, req.cutoff)
    if blocked:
        return fail(blocked, blocked=blocked)

    entry = entry_up(req.entry, req.tick_size)
    stop = down_to_tick(req.stop, req.tick_size)
    target = down_to_tick(req.target, req.tick_size)
    errors = validate_stop(
        entry,
        stop,
        req.tick_size,
        params.decimal("risk.min_stop_distance_pct"),
        params.decimal("risk.max_stop_distance_pct"),
    )
    min_rr = effective_min_rr(params.decimal("risk.min_rr"), req.user_min_rr)
    if "STOP_NOT_BELOW_ENTRY" not in errors:
        errors += validate_rr(entry, stop, target, min_rr)
    if errors:
        return RiskResult(False, tuple(errors), (), None, entry, stop, target, ruleset_version=ver)

    warnings: list[str] = []
    overridden = False
    if req.engine_stop is not None:
        w = stop_override_warning(stop, down_to_tick(req.engine_stop, req.tick_size))
        if w:
            warnings.append(w)
            overridden = True
    sizing = size_position(entry, stop, req.profile, req.state, req.lot_size)
    remaining = max(Decimal(0), req.profile.daily_loss_limit - req.state.day_loss_used)
    rr = risk_reward(entry, stop, target)
    if sizing.rejection:
        return RiskResult(
            False,
            (sizing.rejection,),
            tuple(warnings),
            None,
            entry,
            stop,
            target,
            rr,
            sizing,
            inr(remaining),
            overridden,
            ver,
        )
    return RiskResult(
        True, (), tuple(warnings), None, entry, stop, target, rr, sizing, inr(remaining), overridden, ver
    )
