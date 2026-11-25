"""ORB reference configuration B0, long only (ORB specification §10.3, §12.4; OD-8 Step 2, E4).

A separate detector, not a variant of `detect_opening_range`: it shares none of its behaviour that B0 excludes
(15m context, structure invalidation, target ladder). Pure function of the
bars in `SetupContext` and the ruleset; it reads no clock, tick table or database.

B0 as implemented (every value comes from the ruleset; any other value is refused, because no other variant is
implemented here):
- range: wick basis over the first `session.opening_range_minutes` of 5m bars, validated by the frozen
  `ORB-MG-02` function (`validate_opening_range`, no tolerance); width inside `setup.opening_range_*_pct`;
- breakout: the first 5m close above `OR_HIGH x (1 + setup.breakout_buffer_pct)` ending at or before
  `min(entry cutoff, t_OR + orb.breakout_window_minutes)`; `FIRST_ONLY` (that bar is the breakout and no later
  bar is tried if the risk rules reject it);
- whipsaw: a close below `OR_LOW x (1 - setup.breakout_buffer_pct)` before the breakout ends the setup;
- stop `S-A`: `OR_LOW x (1 - risk.stop_buffer_pct)` rounded down to the tick; target `FIXED_R`:
  `down(E + k R)` with `k = orb.target_k` and `R = E - stop` (see `app.domain.levels.orb_b0_levels`).

Tick checks, price-scale basis, session eligibility and corporate-event exclusion are decided once per
instrument-session upstream (`app.backtest.b0_eligibility`) and shared by the ORB run and its controls.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal

from app.domain.setups.common import after_cutoff, bb, confirm, end, or_end
from app.domain.setups.orb_range import validate_opening_range
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType

SUPPORTED = {
    "orb.range_basis": "WICK",
    "orb.requalify": "FIRST_ONLY",
    "orb.stop_method": "S-A",
    "orb.target_method": "FIXED_R",
}


class UnsupportedOrbParameter(ValueError):
    """A B0 parameter holds a value this implementation does not support (fail closed, never fall back)."""


@dataclass(frozen=True, slots=True)
class OrbB0Setup(Setup):
    """A `Setup` carrying the validated range and the three ORB timestamps (spec §10.4)."""

    range_high: Decimal | None = None
    range_low: Decimal | None = None


def check_b0_parameters(ctx: SetupContext) -> None:
    p = ctx.params
    for key, supported in SUPPORTED.items():
        if p.get(key) != supported:
            raise UnsupportedOrbParameter(f"{key}={p.get(key)!r} is not supported (only {supported!r})")
    if p.decimal("orb.target_k") <= 0 or p.int_("orb.breakout_window_minutes") <= 0:
        raise UnsupportedOrbParameter("orb.target_k and orb.breakout_window_minutes must be positive")


def detect_orb_b0(ctx: SetupContext) -> tuple[list[Setup], list[str]]:
    """Returns `(setups, no_setup_reasons)`; at most one LONG setup, never a SHORT one."""
    check_b0_parameters(ctx)
    p = ctx.params
    minutes = p.int_("session.opening_range_minutes")
    bars = ctx.bars[ctx.first : ctx.t + 1]
    if not any(x.end >= or_end(ctx) for x in bars):
        return [], []  # the range is not formed yet: nothing to judge, nothing to report
    rng = validate_opening_range(bars, ctx.session_open, minutes)
    if not rng.valid:
        assert rng.reason is not None
        return [], [rng.reason.value]
    assert rng.or_high is not None and rng.or_low is not None
    hi, lo = rng.or_high, rng.or_low
    width = (hi - lo) / lo * 100
    if width < p.decimal("setup.opening_range_min_pct"):
        return [], ["OR_TOO_NARROW"]
    if width > p.decimal("setup.opening_range_max_pct"):
        return [], ["OR_TOO_WIDE"]
    o = next(j for j in range(ctx.first, ctx.t + 1) if ctx.bars[j].end >= or_end(ctx))
    window_end = or_end(ctx) + timedelta(minutes=p.int_("orb.breakout_window_minutes"))
    b = bb(ctx)
    setup = Setup(
        SetupType.OPENING_RANGE_BREAKOUT,
        SetupDirection.LONG,
        SetupStatus.AWAITING_CONFIRMATION,
        o,
        hi,
        "OR_HIGH",
        stop_base=lo,
        width_pct=width,
    )
    s = OrbB0Setup(**{f: getattr(setup, f) for f in setup.__slots__}, range_high=hi, range_low=lo)
    for j in range(o + 1, ctx.t + 1):
        bar = ctx.bars[j]
        if after_cutoff(ctx, j):
            return [end(s, SetupStatus.EXPIRED, "SESSION_CUTOFF", j)], []
        if bar.end > window_end:
            return [end(s, SetupStatus.EXPIRED, "AGED_OUT", j)], []
        if bar.close < lo * (1 - b):
            return [end(s, SetupStatus.INVALIDATED, "OR_LOW_BROKEN", j)], []
        if bar.close > hi * (1 + b):
            return [confirm(s, j, bar.close)], []
    return [replace(s)], []
