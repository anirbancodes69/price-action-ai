"""Position sizing (TRD-05 §3)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.risk.account import AccountState, RiskProfile

# Binding constraint -> rejection reason when its quantity is below one.
REJECTION = {
    "RISK_BUDGET": "RISK_BUDGET_TOO_SMALL",
    "CAPITAL": "INSUFFICIENT_CAPITAL",
    "POSITION_CAP": "POSITION_CAP",
    "OPEN_RISK": "OPEN_RISK_LIMIT_REACHED",
    "DAILY_LOSS": "DAILY_LOSS_LIMIT_REACHED",
}


@dataclass(frozen=True, slots=True)
class Sizing:
    qty: int
    risk_budget: Decimal
    risk_per_share: Decimal
    actual_risk: Decimal
    position_value: Decimal
    binding_constraint: str
    constraints: dict[str, int]
    rejection: str | None  # set when qty < 1


def _floor_div(a: Decimal, b: Decimal) -> int:
    return int(max(a, Decimal(0)) // b)


def size_position(
    entry: Decimal,
    stop: Decimal,
    profile: RiskProfile,
    state: AccountState,
    lot_size: int = 1,
) -> Sizing:
    """`qty = min(...)` of the five terms, rounded down to whole lots. Requires `stop < entry`."""
    rps = entry - stop
    if rps <= 0:
        raise ValueError("stop must be below entry")
    budget = profile.capital * profile.risk_pct / 100
    remaining_open = profile.capital * profile.max_open_risk_pct / 100 - state.open_risk
    remaining_daily = profile.daily_loss_limit - state.day_loss_used
    terms = {
        "RISK_BUDGET": _floor_div(budget, rps),
        "CAPITAL": _floor_div(profile.capital - state.cost_basis_open, entry),
        "POSITION_CAP": _floor_div(profile.max_position_value, entry),
        "OPEN_RISK": _floor_div(remaining_open, rps),
        "DAILY_LOSS": _floor_div(remaining_daily, rps),
    }
    binding = min(terms, key=lambda k: terms[k])  # ties: first in the TRD-05 §3 order
    qty = (terms[binding] // lot_size) * lot_size
    return Sizing(
        qty,
        budget,
        rps,
        qty * rps,
        qty * entry,
        binding,
        terms,
        REJECTION[binding] if qty < 1 else None,
    )
