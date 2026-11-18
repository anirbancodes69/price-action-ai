"""Zone break, role reversal and retirement (TRD-03 §5)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.types import Bar, Direction
from app.domain.zones import ZoneStatus


@dataclass(frozen=True, slots=True)
class BreakOutcome:
    status: ZoneStatus
    broken_direction: Direction | None
    broken_at_index: int | None
    retired_at_index: int | None


def evaluate_break(
    bars: Sequence[Bar],
    low: Decimal,
    high: Decimal,
    formed_at_index: int,
    t: int,
    confirm_closes: int,
    buffer: Decimal,
    only: Direction | None = None,
) -> BreakOutcome:
    """Scan closes after formation up to `t` (inclusive).

    `confirm_closes` consecutive closes beyond a bound x buffer break the zone (recorded at the last
    confirming close, §5.1) and flip its role. Consecutive closes beyond the *opposite* bound afterwards
    retire it (§5.2). A single close back inside resets the count (failed break).

    `only` restricts the first break to one direction: a zone that price approaches from one side
    (a resistance zone with price below it) is not "broken" by closes on the side price came from.
    `None` allows either direction (used when the approach side is unknown).
    """
    below_lvl, above_lvl = low * (1 - buffer), high * (1 + buffer)
    status, direction = ZoneStatus.ACTIVE, None
    broken_at: int | None = None
    n_down = n_up = 0
    for j in range(formed_at_index + 1, t + 1):
        c = bars[j].close
        n_down = n_down + 1 if c < below_lvl else 0
        n_up = n_up + 1 if c > above_lvl else 0
        if status is ZoneStatus.ACTIVE:
            if n_down >= confirm_closes and only is not Direction.UP:
                status, direction, broken_at = ZoneStatus.BROKEN_FLIPPED, Direction.DOWN, j
                n_down = n_up = 0
            elif n_up >= confirm_closes and only is not Direction.DOWN:
                status, direction, broken_at = ZoneStatus.BROKEN_FLIPPED, Direction.UP, j
                n_down = n_up = 0
        elif (direction is Direction.DOWN and n_up >= confirm_closes) or (
            direction is Direction.UP and n_down >= confirm_closes
        ):
            return BreakOutcome(ZoneStatus.RETIRED, direction, broken_at, j)
    return BreakOutcome(status, direction, broken_at, None)
