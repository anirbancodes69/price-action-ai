"""Signal on an open long position: `HOLD` or `EXIT` on closed 5m bars (TRD-07 §7.1, TRD-05 §7.2).

The owner trades by hand (ADR-010), so `EXIT` means an exit condition has been met and the exit is
due now. It is decision support, never an order. Only closed bars are used.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.risk.exits import evaluate_bar_exit
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

    Same exit semantics as the backtest (docs/trading/exit-execution-specification.md): each bar from the
    entry is judged by `evaluate_bar_exit`, so a gap through the stop or target at the open, the session-end
    open and the stop-wins-a-collision rule match `step_position`. Only bars that start at or after
    `entry_at` count: an entry bar that began before the fill says nothing about the position (a backtest
    fill is at a bar start, so its fill bar counts in both). A bearish 5m CHoCH that closed on a bar
    (`structure_exit_bars` holds indices into `bars`) is reported at that bar's close; the backtest executes
    it at the next open, which is the same decision, made one bar edge earlier because live code cannot see
    the next bar. After the last bar, `SESSION_END` applies once it has ended at or after the exit time.
    """
    for i, bar in enumerate(bars):
        if bar.start < entry_at:
            continue
        r = evaluate_bar_exit(
            bar,
            stop,
            target,
            session_exit_time=session_exit_time,
            session_exit_enabled=session_exit_enabled,
        )
        if r is not None:
            return PositionSignal("EXIT", r.reason, bar.start if r.reason == "SESSION_END" else bar.end)
        if structure_exit_enabled and i in structure_exit_bars:
            return PositionSignal("EXIT", "STRUCTURE_EXIT", bar.end)
    if session_exit_enabled and session_exit_time is not None and bars and bars[-1].end >= session_exit_time:
        return PositionSignal("EXIT", "SESSION_END", bars[-1].end)
    return PositionSignal("HOLD", None, None)
