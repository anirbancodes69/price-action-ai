"""Stop-loss and risk/reward validation (TRD-05 §4, §5)."""

from __future__ import annotations

from decimal import Decimal


def validate_stop(
    entry: Decimal,
    stop: Decimal,
    tick: Decimal,
    min_distance_pct: Decimal,
    max_distance_pct: Decimal,
) -> list[str]:
    """Errors in rule order. `min_distance_pct` and `max_distance_pct` are percent values (0.15, 2.0)."""
    if stop >= entry:
        return ["STOP_NOT_BELOW_ENTRY"]
    distance = entry - stop
    errors: list[str] = []
    if distance < max(2 * tick, entry * min_distance_pct / 100):
        errors.append("STOP_TOO_TIGHT")
    if distance / entry * 100 > max_distance_pct:
        errors.append("STOP_TOO_WIDE")
    return errors


def stop_override_warning(user_stop: Decimal, engine_stop: Decimal) -> str | None:
    """A stop closer to the entry than the structural stop is allowed but flagged."""
    return "STOP_TIGHTER_THAN_STRUCTURE" if user_stop > engine_stop else None


def effective_min_rr(ruleset_min_rr: Decimal, user_min_rr: Decimal | None) -> Decimal:
    """The user cannot lower the bar below the ruleset value."""
    return ruleset_min_rr if user_min_rr is None else max(ruleset_min_rr, user_min_rr)


def risk_reward(entry: Decimal, stop: Decimal, target: Decimal) -> Decimal | None:
    risk = entry - stop
    return (target - entry) / risk if risk > 0 else None


def validate_rr(entry: Decimal, stop: Decimal, target: Decimal, min_rr: Decimal) -> list[str]:
    if target <= entry:
        return ["TARGET_NOT_ABOVE_ENTRY"]
    rr = risk_reward(entry, stop, target)
    return ["RR_BELOW_MINIMUM"] if rr is None or rr < min_rr else []
