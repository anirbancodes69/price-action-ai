"""``POST /internal/v1/risk/position-size`` and ``/risk/validate-levels`` (ARC-08 §5, TRD-05 v0.2.0)."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.domain.risk.request import MAX_RISK_PER_TRADE_PCT
from app.schemas.common import BookKind, ContractModel, DecimalStr, Direction, RoundedLevels

_VERSION = r"^[0-9]+\.[0-9]+\.[0-9]+$"


class AccountState(ContractModel):
    """Derived state of one book for the current session (TRD-05 §8.1).

    Laravel computes it from the trade tables.
    """

    realised_net_pnl_today: DecimalStr
    open_risk: DecimalStr
    open_cost_basis: DecimalStr = Field(description="Σ cost basis of open positions in this book.")
    open_positions: int = Field(ge=0, description="Open positions plus TRIGGERED plans awaiting fill.")
    losing_streak: int = Field(ge=0)


class PositionSizeRequest(ContractModel):
    """Inputs of TRD-05 §2.

    The plan's levels, the risk profile, the book's account state and the session clock.
    """

    book: BookKind
    direction: Direction
    capital: DecimalStr
    risk_pct: DecimalStr = Field(
        description="Percent of capital risked on the trade, above 0 and at most 2 (a technical "
        "ceiling, not a recommendation; the default is 0.5). Requests above 2 are rejected with 422."
    )
    entry: DecimalStr
    stop: DecimalStr
    target: DecimalStr
    tick_size: DecimalStr
    lot_size: int = Field(default=1, ge=1)
    max_position_value: DecimalStr
    max_open_positions: int = Field(ge=1)
    max_open_risk_pct: DecimalStr
    daily_loss_limit_pct: DecimalStr
    max_consecutive_losses: int = Field(ge=1)
    min_rr: DecimalStr | None = Field(
        default=None, description="User override; only accepted when stricter than the ruleset value."
    )
    account_state: AccountState
    as_of_ts: datetime = Field(description="End of the 5m bar the request is made at (ISO-8601 with offset).")
    entry_cutoff_at: datetime = Field(
        description="Entry cutoff of the session (TRD-01 §4.1), from the calendar."
    )
    ruleset_version: str = Field(pattern=_VERSION)

    @field_validator("risk_pct")
    @classmethod
    def _risk_within_ceiling(cls, v: Decimal) -> Decimal:
        if not 0 < v <= MAX_RISK_PER_TRADE_PCT:
            raise ValueError("risk_pct must be above 0 and at most 2 (technical ceiling, DEC-024)")
        return v


class SizingConstraints(ContractModel):
    """Quantity allowed by each constraint (TRD-05 §3)."""

    qty_risk: int
    qty_capital: int
    qty_position_cap: int
    qty_open_risk: int
    qty_daily_loss: int


class AccountStateResult(ContractModel):
    """Account state as evaluated, with what remains (TRD-05 §8.1, §11)."""

    realised_net_pnl_today: DecimalStr
    open_risk: DecimalStr
    losing_streak: int = Field(ge=0)
    remaining_daily_loss: DecimalStr
    blocked_reason: str | None = Field(
        default=None, description="First failed account rule (TRD-05 §8), e.g. DAILY_LOSS_LIMIT_REACHED."
    )


class RiskResult(ContractModel):
    """Outcome of a sizing calculation. Rule violations are ``errors`` codes from TRD-05, not exceptions."""

    quantity: int = Field(ge=0)
    risk_budget: DecimalStr
    risk_per_share: DecimalStr
    actual_risk: DecimalStr
    actual_risk_pct: DecimalStr
    position_value: DecimalStr
    rr: DecimalStr
    rr_after_costs: DecimalStr
    est_round_trip_costs: DecimalStr
    binding_constraint: str
    constraints: SizingConstraints
    account_state: AccountStateResult
    rounding: RoundedLevels
    warnings: list[str]
    errors: list[str]
    ruleset_version: str = Field(examples=["pa-intraday 0.1.0"])


class AccountLimitsRequest(ContractModel):
    """``POST /internal/v1/risk/account-state``: account limits of one book for the session (TRD-05 §8)."""

    book: BookKind
    capital: DecimalStr
    daily_loss_limit_pct: DecimalStr
    max_consecutive_losses: int = Field(ge=1)
    max_open_positions: int = Field(ge=1)
    account_state: AccountState
    session_open: bool = Field(
        description="Whether the exchange session is open now (from the calendar and the clock)."
    )
    as_of_ts: datetime = Field(description="End of the latest closed 5m bar (ISO-8601 with offset).")
    entry_cutoff_at: datetime


class AccountLimitsResult(ContractModel):
    """The state as evaluated, with the limit values it was checked against."""

    account_state: AccountStateResult
    daily_loss_limit: DecimalStr
    max_consecutive_losses: int
    max_open_positions: int


class LevelsValidationRequest(ContractModel):
    """Validate user-edited levels against the ruleset and the tick size."""

    direction: Direction
    entry: DecimalStr
    stop: DecimalStr
    target: DecimalStr
    tick_size: DecimalStr
    min_rr: DecimalStr | None = None
    ruleset_version: str = Field(pattern=_VERSION)


class LevelsValidationResponse(ContractModel):
    errors: list[str]
    warnings: list[str]
    rounding: RoundedLevels
