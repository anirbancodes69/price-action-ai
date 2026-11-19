"""Signal on an open long position: `HOLD` or `EXIT` on closed 5m bars (TRD-07 §7.1, TRD-05 §7.2).

The owner trades by hand (ADR-010), so `EXIT` means an exit condition has been met and the exit is
due now. It is decision support, never an order. Only closed bars are used.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.types import Bar


@dataclass(frozen=True, slots=True)
class PositionSignal:
    signal: str  # HOLD or EXIT
    reason: str | None  # STOP, TARGET, STRUCTURE_EXIT, SESSION_END
    bar_end: datetime | None  # end of the closed bar on which the condition was met


def monitor_position(
    bars: Sequence[Bar],
    entry_at: datetime,
    stop: Decimal | None,
    target: Decimal | None,
    structure_exit_bars: frozenset[int] = frozenset(),
    session_exit_time: datetime | None = None,
    structure_exit_enabled: bool = True,
    session_exit_enabled: bool = True,
) -> PositionSignal:
    """The signal for a position entered at `entry_at`, given the closed 5m bars up to the latest.

    Only bars that start at or after `entry_at` count: the entry bar itself is partly before the fill,
    so a low or high in it says nothing about the position. Bars are checked in time order and the
    first condition wins: a low at or below the stop (`STOP`, which also wins a stop-and-target bar),
    a high at or above the target (`TARGET`), or a bearish 5m CHoCH that closed on the bar
    (`STRUCTURE_EXIT`; `structure_exit_bars` holds the indices into `bars`). After the last bar,
    `SESSION_END` applies once the latest bar has ended at or after the session-end exit time. A
    missing stop or target is simply never hit.
    """
    for i, bar in enumerate(bars):
        if bar.start < entry_at:
            continue
        if stop is not None and bar.low <= stop:
            return PositionSignal("EXIT", "STOP", bar.end)
        if target is not None and bar.high >= target:
            return PositionSignal("EXIT", "TARGET", bar.end)
        if structure_exit_enabled and i in structure_exit_bars:
            return PositionSignal("EXIT", "STRUCTURE_EXIT", bar.end)
    if session_exit_enabled and session_exit_time is not None and bars and bars[-1].end >= session_exit_time:
        return PositionSignal("EXIT", "SESSION_END", bars[-1].end)
    return PositionSignal("HOLD", None, None)
