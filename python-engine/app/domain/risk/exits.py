"""Exit rules for a long position on a closed 5m bar (TRD-05 §7.2, TRD-06 BT-04)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.types import Bar


@dataclass(frozen=True, slots=True)
class ExitResult:
    price: Decimal
    reason: str  # STOP, TARGET, SESSION_END, STRUCTURE_EXIT
    gap: bool = False  # exited at the bar open


def evaluate_bar_exit(
    bar: Bar,
    stop: Decimal,
    target: Decimal,
    slippage_pct: Decimal = Decimal(0),
    session_exit_time: datetime | None = None,
    session_exit_enabled: bool = True,
    structure_exit_pending: bool = False,
    structure_exit_enabled: bool = True,
) -> ExitResult | None:
    """The exit on `bar`, or `None` while the position stays open.

    Order: gap through the stop or target at the open; session end at the open of the first bar starting at
    the exit time; structure exit at the open (a bearish 5m CHoCH closed on the previous bar); then intrabar
    stop (adverse slippage) and target (no positive slippage). Stop and target in one bar: the stop wins.
    """
    if bar.open <= stop:
        return ExitResult(bar.open, "STOP", gap=True)
    if bar.open >= target:
        return ExitResult(bar.open, "TARGET", gap=True)
    if session_exit_enabled and session_exit_time is not None and bar.start >= session_exit_time:
        return ExitResult(bar.open, "SESSION_END", gap=True)
    if structure_exit_enabled and structure_exit_pending:
        return ExitResult(bar.open, "STRUCTURE_EXIT", gap=True)
    if bar.low <= stop:
        return ExitResult(stop * (1 - slippage_pct / 100), "STOP")
    if bar.high >= target:
        return ExitResult(target, "TARGET")
    return None
