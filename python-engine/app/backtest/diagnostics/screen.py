"""Minimal entries and promotion rules of the fast screening protocol (docs/research/fast-screening-protocol).

Detectors are pure functions of one session's closed 5m bars (chronological, from 09:15): they read bar `s`
only after its close, so a signal never uses a later bar. One signal per symbol per session. Entries are
long; the fill and exit are `sim.fill_and_run`.
"""

from __future__ import annotations

import glob
import pickle
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

from app.backtest.trade import Trade
from app.domain.params import RulesetParams
from app.domain.types import Bar

D = Decimal
TICK = D("0.05")
OR_BARS = 3  # 09:15, 09:20, 09:25: the 15-minute opening range
STOP_FILTERS = (D(0), D("0.75"), D("1.00"))  # percent; 0 = ruleset limits only
PROMOTE_MIN_TRADES = 100
PROMOTE_MIN_EDGE = 0.05
PROMOTE_LEVEL = 0.99
CONFIRM_LEVEL = 0.95


@dataclass(frozen=True, slots=True)
class EntryParams:
    bb: Decimal  # breakout / break buffer, percent
    sb: Decimal  # stop buffer, percent
    or_min_pct: Decimal
    or_max_pct: Decimal
    reclaim_bars: int
    min_stop_pct: Decimal
    max_stop_pct: Decimal


def entry_params(p: RulesetParams) -> EntryParams:
    return EntryParams(
        p.decimal("setup.breakout_buffer_pct"),
        p.decimal("risk.stop_buffer_pct"),
        p.decimal("setup.opening_range_min_pct"),
        p.decimal("setup.opening_range_max_pct"),
        p.int_("setup.failed_break_max_bars"),
        p.decimal("risk.min_stop_distance_pct"),
        p.decimal("risk.max_stop_distance_pct"),
    )


@dataclass(frozen=True, slots=True)
class Signal:
    entry: str  # M1, M2 or M3
    index: int  # signal bar (its close is the reference entry)
    ref: Decimal
    stop: Decimal

    @property
    def stop_pct(self) -> Decimal:
        return (self.ref - self.stop) / self.ref * 100


def floor_tick(x: Decimal, tick: Decimal = TICK) -> Decimal:
    return (x / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def _after_or(bars: Sequence[Bar]) -> range:
    """Bars that start after the opening range (09:30 onward)."""
    return range(OR_BARS, len(bars))


def opening_range(bars: Sequence[Bar]) -> tuple[Decimal, Decimal] | None:
    if len(bars) <= OR_BARS:
        return None
    return max(b.high for b in bars[:OR_BARS]), min(b.low for b in bars[:OR_BARS])


def detect_m1(bars: Sequence[Bar], p: EntryParams) -> Signal | None:
    """Opening-range breakout: first bar after the range closing above `OR_HIGH * (1 + bb)`; range width
    inside the gate; stop `OR_LOW * (1 - sb)`."""
    rng = opening_range(bars)
    if rng is None:
        return None
    high, low = rng
    width = (high - low) / low * 100
    if not p.or_min_pct <= width <= p.or_max_pct:
        return None
    for s in _after_or(bars):
        if bars[s].close > high * (1 + p.bb / 100):
            return Signal("M1", s, bars[s].close, floor_tick(low * (1 - p.sb / 100)))
    return None


def detect_m2(bars: Sequence[Bar], p: EntryParams, pdh: Decimal | None) -> Signal | None:
    """Previous-day-high break: the session opens below `PDH`; first bar after the range closing above
    `PDH * (1 + bb)`; stop the lowest low of the session so far `* (1 - sb)`."""
    if pdh is None or not bars or bars[0].open >= pdh:
        return None
    for s in _after_or(bars):
        if bars[s].close > pdh * (1 + p.bb / 100):
            low = min(b.low for b in bars[: s + 1])
            return Signal("M2", s, bars[s].close, floor_tick(low * (1 - p.sb / 100)))
    return None


def detect_m3(bars: Sequence[Bar], p: EntryParams) -> Signal | None:
    """Failed opening-range breakdown: the first bar after the range closing below `OR_LOW * (1 - bb)`, then
    the first bar within `reclaim_bars` closing at or above `OR_LOW`; the signal is the reclaim bar; stop the
    lowest low from the breakdown to the reclaim `* (1 - sb)`. Only the first breakdown is considered."""
    rng = opening_range(bars)
    if rng is None:
        return None
    low = rng[1]
    for b in _after_or(bars):
        if bars[b].close < low * (1 - p.bb / 100):
            for r in range(b + 1, min(b + p.reclaim_bars, len(bars) - 1) + 1):
                if bars[r].close >= low:
                    lowest = min(x.low for x in bars[b : r + 1])
                    return Signal("M3", r, bars[r].close, floor_tick(lowest * (1 - p.sb / 100)))
            return None
    return None


def detect(entry: str, bars: Sequence[Bar], p: EntryParams, pdh: Decimal | None = None) -> Signal | None:
    if entry == "M1":
        return detect_m1(bars, p)
    if entry == "M2":
        return detect_m2(bars, p, pdh)
    if entry == "M3":
        return detect_m3(bars, p)
    raise ValueError(f"unknown entry {entry}")


def passes_stop(stop_pct: Decimal, flt: Decimal, p: EntryParams) -> bool:
    """Ruleset stop limits (0.15% to 2.0%) and the variant's minimum stop distance."""
    return max(p.min_stop_pct, flt) <= stop_pct <= p.max_stop_pct


def variant_id(entry: str, flt: Decimal) -> str:
    return f"{entry}@{'none' if flt == 0 else f'>={flt}%'}"


def tier1_variants() -> list[tuple[str, str, Decimal]]:
    return [(variant_id(e, f), e, f) for e in ("M1", "M2", "M3") for f in STOP_FILTERS]


def promoted(n: int, gross_avg: float, diff_est: float, diff_low: float) -> bool:
    """Promotion from the screen (protocol §5): at least 100 trades, gross average above zero, gross edge over
    the control of at least +0.05R, 99% interval above zero."""
    return n >= PROMOTE_MIN_TRADES and gross_avg > 0 and diff_est >= PROMOTE_MIN_EDGE and diff_low > 0


def confirmed(n: int, diff_est: float, diff_low: float, half_diffs: Sequence[float]) -> bool:
    """Confirmation (protocol §5): at least 100 trades, edge at least +0.05R with the 95% interval above zero,
    and the same (positive) sign in each half of the segment."""
    return (
        n >= PROMOTE_MIN_TRADES
        and diff_est >= PROMOTE_MIN_EDGE
        and diff_low > 0
        and len(half_diffs) == 2
        and all(d > 0 for d in half_diffs)
    )


def session_halves(days: Sequence[date]) -> tuple[set[date], set[date]]:
    """Split the sorted unique session dates into two halves (the first gets the odd one out)."""
    ordered = sorted(set(days))
    k = (len(ordered) + 1) // 2
    return set(ordered[:k]), set(ordered[k:])


def load_trades(directory: Path) -> dict[str, list[Trade]]:
    """Trades by symbol from the chunk files of one 4a run (own harness files, see app/backtest/chunks.py)."""
    out: dict[str, list[Trade]] = defaultdict(list)
    for f in sorted(glob.glob(str(directory / "*.pkl"))):
        payload = pickle.loads(Path(f).read_bytes())  # noqa: S301 - own harness files
        for sess in payload["sessions"]:
            for t in sess.trades:
                out[t.symbol].append(t)
    return out
