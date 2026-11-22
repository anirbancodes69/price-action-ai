"""R decomposition (DX-3) and the independent trade check (DX-7) on saved trades and stored bars."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.backtest.trade import Trade
from app.domain.types import Bar

D = Decimal
BUCKETS = ((D("0.15"), D("0.30")), (D("0.30"), D("0.50")), (D("0.50"), D("1.00")), (D("1.00"), D("2.00")))


@dataclass(frozen=True, slots=True)
class Decomposition:
    """One trade in units of R (its own risk amount). `before_friction` adds the two slippage items back
    to the gross R, so `r_net = before_friction - entry_slip - stop_slip - charges` exactly."""

    stop_pct: float
    r_gross: float
    r_net: float
    before_friction: float
    entry_slip: float
    stop_slip: float
    charges: float
    fill_gap: float  # fill-bar open minus the previous bar's close (not part of the identity)


def stop_of(t: Trade) -> Decimal:
    """Stop price of a saved trade: `risk_amount = qty * (entry - stop)`."""
    return t.entry - t.risk_amount / t.qty


def stop_pct_of(t: Trade) -> Decimal:
    return (t.entry - stop_of(t)) / t.entry * 100


def bucket_of(stop_pct: Decimal) -> int:
    """Index into `BUCKETS`, or -1 outside them (below the minimum or above the maximum stop)."""
    for k, (lo, hi) in enumerate(BUCKETS):
        if lo <= stop_pct < hi or (k == len(BUCKETS) - 1 and stop_pct == hi):
            return k
    return -1


def decompose(t: Trade, fill_bar: Bar, prev_close: Decimal | None, slippage_pct: Decimal) -> Decomposition:
    risk = t.risk_amount
    entry_slip = (t.entry - fill_bar.open) * t.qty  # the slippage added to the open
    stop_slip = D(0)
    if t.reason == "STOP":
        stop_slip = (stop_of(t) - t.exit) * t.qty
    elif t.reason == "STOP_GAP":
        stop_slip = (t.exit / (1 - slippage_pct / 100) - t.exit) * t.qty
    gap = (fill_bar.open - prev_close) * t.qty if prev_close is not None else D(0)
    return Decomposition(
        float(stop_pct_of(t)),
        float(t.r_gross),
        float(t.r_net),
        float((t.gross_pnl + entry_slip + stop_slip) / risk),
        float(entry_slip / risk),
        float(stop_slip / risk),
        float(t.costs / risk),
        float(gap / risk),
    )


def verify_trade(bars: Sequence[Bar], t: Trade, slippage_pct: Decimal, exit_time: datetime) -> list[str]:
    """Recompute the fill and exit of a saved trade from the raw bars with separate logic; list mismatches.

    The target is not stored, so a `TARGET` exit is checked for plausibility only (the exit bar's high
    reaches the exit price and no earlier bar stopped the trade)."""
    out: list[str] = []
    idx = {b.start: k for k, b in enumerate(bars)}
    if t.fill_at not in idx:
        return ["fill bar missing from the stored bars"]
    i = idx[t.fill_at]
    if t.entry != bars[i].open * (1 + slippage_pct / 100):
        out.append(f"entry {t.entry} != open {bars[i].open} plus slippage")
    stop = stop_of(t)
    expected: tuple[Decimal, str, datetime] | None = None
    for j in range(i, len(bars)):
        b = bars[j]
        if b.open <= stop:
            expected = (b.open * (1 - slippage_pct / 100), "STOP_GAP", b.start)
        elif b.start >= exit_time:
            expected = (b.open, "SESSION_END", b.start)
        elif b.low <= stop:
            expected = (stop * (1 - slippage_pct / 100), "STOP", b.start)
        elif t.reason in ("TARGET", "TARGET_GAP") and b.start == t.exit_at and b.high >= t.exit:
            expected = (t.exit, t.reason, b.start)
        if expected is not None:
            break
    if expected is None:
        return [*out, "no exit found in the stored bars"]
    price, reason, at = expected
    coll = reason == "STOP" and t.reason == "STOP_COLLISION"
    if at != t.exit_at:
        out.append(f"exit time {t.exit_at} != {at}")
    if reason != t.reason and not coll:
        out.append(f"exit reason {t.reason} != {reason}")
    if abs(price - t.exit) > D("0.000001"):
        out.append(f"exit price {t.exit} != {price}")
    if abs((t.exit - t.entry) * t.qty - t.gross_pnl) > D("0.000001"):
        out.append("gross P&L != (exit - entry) * qty")
    if abs(t.gross_pnl / t.risk_amount - t.r_gross) > D("0.000001"):
        out.append("gross R != gross P&L / risk")
    return out
