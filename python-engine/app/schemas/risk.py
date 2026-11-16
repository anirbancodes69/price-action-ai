"""``POST /internal/v1/risk/position-size`` and ``/risk/validate-levels`` (ARC-08 §5, TRD-05)."""

from pydantic import Field

from app.schemas.common import BookKind, ContractModel, DecimalStr, Direction, RoundedLevels


class OpenPosition(ContractModel):
    """One open position in the same book as the plan (TRD-05 §2)."""

    cost_basis: DecimalStr
    open_risk: DecimalStr


class PositionSizeRequest(ContractModel):
    """Inputs of TRD-05 §2. Laravel supplies capital, the risk profile and the open positions of one book."""

    book: BookKind
    direction: Direction
    capital: DecimalStr
    risk_pct: DecimalStr
    entry: DecimalStr
    stop: DecimalStr
    target: DecimalStr
    tick_size: DecimalStr
    lot_size: int = Field(default=1, ge=1)
    open_positions: list[OpenPosition] = Field(default_factory=list)
    max_open_positions: int = Field(ge=1)
    max_heat_pct: DecimalStr
    max_position_pct: DecimalStr
    min_rr: DecimalStr | None = Field(
        default=None, description="User override; only accepted when stricter than the ruleset value."
    )
    ruleset_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")


class SizingConstraints(ContractModel):
    """Quantity allowed by each constraint (TRD-05 §3)."""

    qty_risk: int
    qty_capital: int
    qty_position_cap: int
    qty_heat: int


class RiskResult(ContractModel):
    """Outcome of a sizing calculation. Rule violations are ``errors`` codes from TRD-05, not exceptions."""

    quantity: int = Field(ge=0)
    risk_budget: DecimalStr
    risk_per_share: DecimalStr
    actual_risk: DecimalStr
    actual_risk_pct: DecimalStr
    position_value: DecimalStr
    rr: DecimalStr
    binding_constraint: str
    constraints: SizingConstraints
    rounding: RoundedLevels
    warnings: list[str]
    errors: list[str]
    ruleset_version: str = Field(examples=["pa-core 0.1.0"])


class LevelsValidationRequest(ContractModel):
    """Validate user-edited levels against the ruleset and the tick size."""

    direction: Direction
    entry: DecimalStr
    stop: DecimalStr
    target: DecimalStr
    tick_size: DecimalStr
    min_rr: DecimalStr | None = None
    ruleset_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")


class LevelsValidationResponse(ContractModel):
    errors: list[str]
    warnings: list[str]
    rounding: RoundedLevels
