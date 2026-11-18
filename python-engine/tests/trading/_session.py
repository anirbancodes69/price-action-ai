"""Session fixtures for setup tests: a day of 5m bars built from (open, high, low, close) strings."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.htf import HtfContext, align_htf
from app.domain.params import RulesetParams
from app.domain.pivots import detect_pivots, label_pivots
from app.domain.session import SessionLevels, session_levels
from app.domain.setups.types import SetupContext
from app.domain.structure import run_structure
from app.domain.types import Bar, BarState, StructureState
from app.rulesets import load_ruleset

D = Decimal
OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST
CLOSE = OPEN + timedelta(hours=6, minutes=15)  # 15:30 IST
PARAMS = load_ruleset("pa-intraday", "0.1.0")


def mk(rows: Sequence[tuple[str, str, str, str]], start: datetime = OPEN) -> list[Bar]:
    out = []
    for i, (o, h, lo, c) in enumerate(rows):
        s = start + timedelta(minutes=5 * i)
        out.append(Bar(s, s + timedelta(minutes=5), D(o), D(h), D(lo), D(c)))
    return out


def flat_htf(n: int, state: StructureState = StructureState.BULLISH) -> list[HtfContext]:
    st = BarState(state, None, None, None)
    return [HtfContext(0, st) for _ in range(n)]


def ctx_for(
    bars: list[Bar],
    pdh: str | None = None,
    pdl: str | None = None,
    htf: list[HtfContext] | None = None,
    params: RulesetParams = PARAMS,
    cutoff_minutes: int = 45,
) -> SetupContext:
    from app.domain.session import DailyLevels

    prev = DailyLevels(D(pdh), D(pdl), D("0")) if pdh and pdl else None
    lv = session_levels(bars, OPEN, prev, params.int_("session.opening_range_minutes"))
    if pdh and not pdl:
        lv = SessionLevels(D(pdh), None, None, lv.or_high, lv.or_low, lv.session_high, lv.session_low)
    piv = label_pivots(detect_pivots(bars, 2, 2), params.equal_tolerance())
    struct = run_structure(bars, piv, params.break_buffer("5m"))
    return SetupContext(
        bars,
        0,
        len(bars) - 1,
        OPEN,
        CLOSE - timedelta(minutes=cutoff_minutes),
        lv,
        htf if htf is not None else flat_htf(len(bars)),
        struct,
        piv,
        [],
        None,
        params,
    )


def align_for_test(bars: list[Bar], bars15: list[Bar]) -> list[HtfContext]:
    s15 = run_structure(bars15, label_pivots(detect_pivots(bars15, 2, 2), D("0.001")), D("0.0005"))
    return align_htf([b.end for b in bars], bars15, s15)
