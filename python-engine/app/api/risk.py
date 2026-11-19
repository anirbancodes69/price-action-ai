"""``POST /internal/v1/risk/position-size`` and ``/risk/validate-levels`` (ARC-08 §5, TRD-05)."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import ruleset_for
from app.backtest.costs import CostSchedule, intraday_costs
from app.domain.risk.account import AccountState as DomainState
from app.domain.risk.account import RiskProfile, check_account_limits
from app.domain.risk.request import RiskRequest, calculate_risk
from app.domain.risk.rounding import down_to_tick, entry_up
from app.domain.risk.validation import effective_min_rr, validate_rr, validate_stop
from app.domain.setups.types import SetupDirection
from app.schemas.common import Direction, RoundedLevels
from app.schemas.risk import (
    AccountLimitsRequest,
    AccountLimitsResult,
    AccountStateResult,
    LevelsValidationRequest,
    LevelsValidationResponse,
    PositionSizeRequest,
    RiskResult,
    SizingConstraints,
)
from app.settings import Settings, get_settings

router = APIRouter(prefix="/risk")
ZERO = Decimal(0)
COSTS_WARNING = "COSTS_UNVERIFIED"  # the TRD-06 §5 schedule is an unverified assumption (OQ-BT-02)


def _direction(d: Direction) -> SetupDirection:
    return SetupDirection.LONG if d is Direction.LONG else SetupDirection.SHORT


def _state(req: PositionSizeRequest) -> DomainState:
    a = req.account_state
    loss = max(ZERO, -a.realised_net_pnl_today)
    return DomainState(
        a.realised_net_pnl_today,
        loss,
        a.open_risk,
        loss + a.open_risk,
        a.losing_streak,
        a.open_positions,
        a.open_cost_basis,
    )


@router.post("/position-size")
def position_size(
    req: PositionSizeRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> RiskResult:
    """Pure calculation: Laravel supplies the profile, the book's account state and the session clock."""
    params = ruleset_for(settings, req.ruleset_version)
    profile = RiskProfile(
        req.capital,
        req.risk_pct,
        req.max_position_value,
        req.daily_loss_limit_pct,
        req.max_consecutive_losses,
        req.max_open_positions,
        req.max_open_risk_pct,
    )
    state = _state(req)
    r = calculate_risk(
        RiskRequest(
            _direction(req.direction),
            req.entry,
            req.stop,
            req.target,
            req.tick_size,
            req.lot_size,
            profile,
            state,
            True,
            req.as_of_ts,
            req.entry_cutoff_at,
            req.min_rr,
        ),
        params,
    )
    rounded = RoundedLevels(
        entry=entry_up(req.entry, req.tick_size),
        stop=down_to_tick(req.stop, req.tick_size),
        target=down_to_tick(req.target, req.tick_size),
    )
    remaining = max(ZERO, profile.daily_loss_limit - state.day_loss_used)
    acct = AccountStateResult(
        realised_net_pnl_today=state.realised_net_pnl_today,
        open_risk=state.open_risk,
        losing_streak=state.losing_streak,
        remaining_daily_loss=remaining,
        blocked_reason=r.blocked_reason,
    )
    ver = r.ruleset_version or f"{params.code} {params.version}"
    sz = r.sizing
    if not r.ok or sz is None:
        return RiskResult(
            quantity=0,
            risk_budget=sz.risk_budget if sz else ZERO,
            risk_per_share=sz.risk_per_share if sz else ZERO,
            actual_risk=ZERO,
            actual_risk_pct=ZERO,
            position_value=ZERO,
            rr=r.rr or ZERO,
            rr_after_costs=ZERO,
            est_round_trip_costs=ZERO,
            binding_constraint=sz.binding_constraint if sz else "NOT_SIZED",
            constraints=_constraints(sz.constraints if sz else {}),
            account_state=acct,
            rounding=rounded,
            warnings=list(r.warnings),
            errors=list(r.errors),
            ruleset_version=ver,
        )
    qty = sz.qty
    costs = intraday_costs(rounded.entry * qty, rounded.target * qty, CostSchedule()).total
    gross = (rounded.target - rounded.entry) * qty
    return RiskResult(
        quantity=qty,
        risk_budget=sz.risk_budget,
        risk_per_share=sz.risk_per_share,
        actual_risk=sz.actual_risk,
        actual_risk_pct=sz.actual_risk / req.capital * 100,
        position_value=sz.position_value,
        rr=r.rr or ZERO,
        rr_after_costs=(gross - costs) / sz.actual_risk,
        est_round_trip_costs=costs,
        binding_constraint=sz.binding_constraint,
        constraints=_constraints(sz.constraints),
        account_state=acct,
        rounding=rounded,
        warnings=[*r.warnings, COSTS_WARNING],
        errors=[],
        ruleset_version=ver,
    )


def _constraints(c: dict[str, int]) -> SizingConstraints:
    return SizingConstraints(
        qty_risk=c.get("RISK_BUDGET", 0),
        qty_capital=c.get("CAPITAL", 0),
        qty_position_cap=c.get("POSITION_CAP", 0),
        qty_open_risk=c.get("OPEN_RISK", 0),
        qty_daily_loss=c.get("DAILY_LOSS", 0),
    )


@router.post("/account-state")
def account_state(req: AccountLimitsRequest) -> AccountLimitsResult:
    """Apply the account limits: what remains, and the first rule that blocks new entries."""
    a = req.account_state
    loss = max(ZERO, -a.realised_net_pnl_today)
    state = DomainState(
        a.realised_net_pnl_today,
        loss,
        a.open_risk,
        loss + a.open_risk,
        a.losing_streak,
        a.open_positions,
        a.open_cost_basis,
    )
    profile = RiskProfile(
        req.capital,
        ZERO,  # not used by the account limits
        ZERO,
        req.daily_loss_limit_pct,
        req.max_consecutive_losses,
        req.max_open_positions,
        ZERO,
    )
    return AccountLimitsResult(
        account_state=AccountStateResult(
            realised_net_pnl_today=state.realised_net_pnl_today,
            open_risk=state.open_risk,
            losing_streak=state.losing_streak,
            remaining_daily_loss=max(ZERO, profile.daily_loss_limit - state.day_loss_used),
            blocked_reason=check_account_limits(
                state, profile, req.session_open, req.as_of_ts, req.entry_cutoff_at
            ),
        ),
        daily_loss_limit=profile.daily_loss_limit,
        max_consecutive_losses=req.max_consecutive_losses,
        max_open_positions=req.max_open_positions,
    )


@router.post("/validate-levels")
def validate_levels(
    req: LevelsValidationRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> LevelsValidationResponse:
    """Validate user-edited levels: SHORT, stop distance, target and the R:R floor (TRD-05 §4-§6)."""
    params = ruleset_for(settings, req.ruleset_version)
    entry = entry_up(req.entry, req.tick_size)
    stop = down_to_tick(req.stop, req.tick_size)
    target = down_to_tick(req.target, req.tick_size)
    errors: list[str] = []
    if req.direction is not Direction.LONG:
        errors.append("SHORT_NOT_SUPPORTED")
    else:
        errors += validate_stop(
            entry,
            stop,
            req.tick_size,
            params.decimal("risk.min_stop_distance_pct"),
            params.decimal("risk.max_stop_distance_pct"),
        )
        if "STOP_NOT_BELOW_ENTRY" not in errors:
            errors += validate_rr(
                entry, stop, target, effective_min_rr(params.decimal("risk.min_rr"), req.min_rr)
            )
    return LevelsValidationResponse(
        errors=errors, warnings=[], rounding=RoundedLevels(entry=entry, stop=stop, target=target)
    )
