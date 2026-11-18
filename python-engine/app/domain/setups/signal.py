"""Primary setup selection and signal mapping (TRD-04 §12)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.levels import TradeLevels
from app.domain.setups.scoring import Paqs
from app.domain.setups.types import TYPE_ORDER, Setup, SetupContext, SetupDirection, SetupStatus


class Signal(StrEnum):
    """Analysis-run signals. `HOLD` and `EXIT` come from the trade monitor only (TRD-07)."""

    NO_TRADE = "NO_TRADE"
    BUY_WATCH = "BUY_WATCH"
    ENTRY_CONFIRMED = "ENTRY_CONFIRMED"


@dataclass(frozen=True, slots=True)
class ScoredSetup:
    setup: Setup
    paqs: Paqs | None
    levels: TradeLevels | None


@dataclass(frozen=True, slots=True)
class SignalResult:
    signal: Signal
    primary: ScoredSetup | None
    reasons: tuple[str, ...]
    signal_at: datetime
    valid_until: datetime | None


def _priority(s: ScoredSetup, t: int) -> tuple[int, int, int, int]:
    st = s.setup.status
    rank = 0 if st is SetupStatus.ENTRY_CONFIRMED else 1 if st is SetupStatus.AWAITING_CONFIRMATION else 2
    score = s.paqs.total if s.paqs else 0
    return rank, -score, -s.setup.detected_at_index, TYPE_ORDER[s.setup.type]


def _eligible(s: ScoredSetup, t: int) -> bool:
    st = s.setup.status
    if s.setup.direction is not SetupDirection.LONG:
        return False
    if st is SetupStatus.ENTRY_CONFIRMED:
        return s.setup.confirmed_at_index == t
    return st in (SetupStatus.FORMING, SetupStatus.AWAITING_CONFIRMATION)


def choose_signal(
    scored: Sequence[ScoredSetup], ctx: SetupContext, extra_reasons: Sequence[str] = ()
) -> SignalResult:
    """TRD-04 §12. `signal_at = E(T)`; `valid_until` per signal type."""
    t = ctx.t
    bar = ctx.bars[t]
    signal_at = bar.end
    step = bar.end - bar.start
    pool = sorted((s for s in scored if _eligible(s, t)), key=lambda s: _priority(s, t))
    if not pool:
        return SignalResult(Signal.NO_TRADE, None, ("NO_SETUP", *extra_reasons), signal_at, None)
    primary = pool[0]
    reasons: list[str] = []
    if primary.paqs is None or primary.paqs.total < ctx.params.int_("score.watch_threshold"):
        reasons.append("LOW_SCORE")
    if primary.levels is None or primary.levels.rr_below_min:
        reasons.append("RR_BELOW_MINIMUM" if primary.levels and primary.levels.target else "NO_TARGET")
    if signal_at > ctx.cutoff:
        reasons.append("AFTER_ENTRY_CUTOFF")
    if reasons:
        return SignalResult(Signal.NO_TRADE, primary, tuple(reasons), signal_at, None)
    if primary.setup.status is SetupStatus.ENTRY_CONFIRMED:
        return SignalResult(Signal.ENTRY_CONFIRMED, primary, (), signal_at, signal_at + step)
    expiry_end = bar_end_at(ctx, primary.setup.detected_at_index) + step * ctx.params.int_(
        "setup.expiry_bars"
    )
    return SignalResult(Signal.BUY_WATCH, primary, (), signal_at, min(expiry_end, ctx.cutoff))


def bar_end_at(ctx: SetupContext, index: int) -> datetime:
    return ctx.bars[index].end
