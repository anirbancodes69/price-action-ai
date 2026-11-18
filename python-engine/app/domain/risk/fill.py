"""Entry fill rule at the next 5m open (TRD-05 §7.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FillResult:
    filled: bool
    price: Decimal | None
    qty: int
    reason: str | None  # SKIPPED_* when not filled


def simulate_entry(
    open_price: Decimal,
    entry_ref: Decimal,
    stop: Decimal,
    target: Decimal,
    qty_plan: int,
    risk_budget: Decimal,
    max_position_value: Decimal,
    min_rr: Decimal,
    max_entry_gap_pct: Decimal,
    bar_start: datetime,
    cutoff: datetime,
    slippage_pct: Decimal = Decimal(0),
    account_blocked: str | None = None,
) -> FillResult:
    """Fill at the open of the bar after `ENTRY_CONFIRMED`, or skip with a reason.

    Checks in spec order: cutoff, gap through the stop, gap up beyond `max_entry_gap_pct`, degraded R:R.
    Quantity is re-checked and **never increased** at fill. `slippage_pct` (percent, adverse) raises the fill.
    `account_blocked` carries a limit reached since the plan was made (TRD-05 §7.1 re-evaluation).
    """
    if bar_start >= cutoff:
        return FillResult(False, None, 0, "SKIPPED_SESSION_CUTOFF")
    if open_price <= stop:
        return FillResult(False, None, 0, "SKIPPED_GAP_BELOW_STOP")
    if open_price > entry_ref * (1 + max_entry_gap_pct / 100):
        return FillResult(False, None, 0, "SKIPPED_GAP_UP")
    price = open_price * (1 + slippage_pct / 100)
    if price <= stop or (target - price) / (price - stop) < min_rr:
        return FillResult(False, None, 0, "SKIPPED_RR_DEGRADED")
    if account_blocked is not None:
        return FillResult(False, None, 0, "SKIPPED_ACCOUNT_LIMIT")
    qty = min(qty_plan, int(risk_budget // (price - stop)), int(max_position_value // price))
    if qty < 1:
        return FillResult(False, None, 0, "SKIPPED_SIZE")
    return FillResult(True, price, qty, None)
