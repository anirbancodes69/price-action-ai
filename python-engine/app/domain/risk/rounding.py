"""Conservative rounding (TRD-05 §6, RM-05)."""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal


def entry_up(price: Decimal, tick: Decimal | None) -> Decimal:
    """Long entry rounds up to the next tick (`None`: provider-adjusted scale, no rounding, OD-8 D3)."""
    if tick is None:
        return price
    return (price / tick).to_integral_value(ROUND_CEILING) * tick


def down_to_tick(price: Decimal, tick: Decimal | None) -> Decimal:
    """Stops and targets round down (`None`: no rounding)."""
    if tick is None:
        return price
    return (price / tick).to_integral_value(ROUND_FLOOR) * tick


def qty_to_lots(qty: int, lot_size: int) -> int:
    return (qty // lot_size) * lot_size


def inr(amount: Decimal) -> Decimal:
    """INR amounts: 2 decimals, ROUND_HALF_UP (RM-06)."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
