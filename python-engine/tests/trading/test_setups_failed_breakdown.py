"""FAILED_BREAKDOWN_RECLAIM (Strategy 02 specification §7-§13). Every expected value is hand-computed.

Constants (`pa-intraday 0.4.0`): sbuf = bb = sb = 0.05%, N = 6, expiry 12 bars, tick unset (no rounding).
Level Y = PDL 1480: `Y x (1 - sbuf)` = 1479.26; confirmation needs a close above `trigger x 1.0005`.
"""

from __future__ import annotations

import pytest

from app.domain.levels import trade_levels
from app.domain.params import RulesetParams
from app.domain.setups.failed_breakdown import detect_failed_breakdown, failed_breakout_enabled
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.strategies import strategy_detectors
from app.rulesets import load_ruleset

from ._session import D, ctx_for, mk
from .test_setups_sweep import LEAD

FAILED = load_ruleset("pa-intraday", "0.4.0")
Row = tuple[str, str, str, str]

BREAK: Row = ("1482", "1482", "1476", "1477")  # bar 5: close 1477 < 1479.26, the first close below PDL
RECLAIM: Row = ("1477", "1481", "1476.5", "1480.5")  # bar 6: close 1480.5 >= 1480; H 1481, break low 1476
CONFIRM: Row = ("1480.5", "1483", "1480", "1482")  # bar 7: close 1482 > 1481 x 1.0005 = 1481.7405
BELOW: Row = ("1477", "1479", "1476.5", "1478")  # stays below PDL without a new low or a reclaim
HOLD: Row = ("1480", "1481", "1479.6", "1480.5")  # above 1479.26, below the confirmation level
SEQ = [*LEAD, BREAK, RECLAIM, CONFIRM]


def _ctx(rows: list[Row], params: RulesetParams = FAILED, **kw: object) -> SetupContext:
    kw.setdefault("pdh", "1510")
    kw.setdefault("pdl", "1480")
    return ctx_for(mk(rows), params=params, **kw)  # type: ignore[arg-type]


def _setups(rows: list[Row], **kw: object) -> list[Setup]:
    return detect_failed_breakdown(_ctx(rows, **kw))[0]


def _with(**over: object) -> RulesetParams:
    return RulesetParams(FAILED.code, FAILED.version, {**FAILED.values, **over})


def test_disabled_before_0_4_0_and_registered_as_a_strategy() -> None:
    for v in ("0.1.0", "0.2.0", "0.3.0"):
        assert not failed_breakout_enabled(load_ruleset("pa-intraday", v))
        assert detect_failed_breakdown(_ctx(SEQ, params=load_ruleset("pa-intraday", v))) == ([], [])
    assert failed_breakout_enabled(FAILED)
    assert strategy_detectors("failed_breakout") == (detect_failed_breakdown,)


def test_breakdown_by_close_and_reclaim_by_close_then_confirmation() -> None:
    [s] = _setups(SEQ)
    assert (s.type, s.direction, s.anchor) == (SetupType.FAILED_BREAKDOWN_RECLAIM, SetupDirection.LONG, "PDL")
    # Breakdown bar 5, reclaim bar 6: trigger H[6] = 1481, break low min(1476, 1476.5) = 1476 is the stop base.
    assert (s.breakdown_index, s.detected_at_index, s.trigger_price) == (5, 6, D("1481"))
    assert (s.swept_level, s.sweep_low, s.stop_base) == (D("1480"), D("1476"), D("1476"))
    assert (s.status, s.confirmed_at_index, s.confirm_close) == (SetupStatus.ENTRY_CONFIRMED, 7, D("1482"))


def test_awaiting_confirmation_before_the_trigger_closes() -> None:
    [s] = _setups([*LEAD, BREAK, RECLAIM])
    assert (s.status, s.detected_at_index, s.confirmed_at_index) == (
        SetupStatus.AWAITING_CONFIRMATION,
        6,
        None,
    )


def test_a_wick_below_the_level_that_closes_above_the_buffer_is_not_a_breakdown() -> None:
    # Low 1476 < 1479.26 but close 1481 >= 1479.26: Strategy 01's event, not this one.
    wick: Row = ("1482", "1483", "1476", "1481")
    rows = [*LEAD, wick, RECLAIM, CONFIRM]
    assert _setups(rows) == []
    assert len(detect_liquidity_sweep(_ctx(rows, params=load_ruleset("pa-intraday", "0.3.0")))[0]) == 1


def test_reclaim_exactly_at_the_window_edge_and_one_bar_later() -> None:
    edge = [*LEAD, BREAK, *[BELOW] * 5, RECLAIM]  # breakdown 5, reclaim 11 = 5 + N
    [s] = _setups(edge)
    assert (s.breakdown_index, s.detected_at_index, s.stop_base) == (5, 11, D("1476"))
    assert _setups([*LEAD, BREAK, *[BELOW] * 6, RECLAIM]) == []  # reclaim at 12 = 5 + N + 1


def test_window_comes_from_the_ruleset() -> None:
    rows = [*LEAD, BREAK, *[BELOW] * 6, RECLAIM]  # reclaim 7 bars after the breakdown
    assert _setups(rows, params=_with(**{"setup.failed_break_max_bars": 7})) != []
    assert _setups(rows, params=_with(**{"setup.failed_break_max_bars": 6})) == []


def test_no_reclaim_in_the_window_gives_no_setup() -> None:
    assert _setups([*LEAD, BREAK, *[BELOW] * 4]) == []


def test_a_level_already_broken_is_not_a_breakdown_again_and_is_used_once() -> None:
    out = _setups(
        [*LEAD, BREAK, RECLAIM, BREAK, RECLAIM]
    )  # bars 7 and 8 break and reclaim the same PDL again
    assert [s.breakdown_index for s in out] == [5]


def test_break_resumed_invalidates_before_confirmation() -> None:
    resumed: Row = ("1480", "1480", "1478", "1479")  # close 1479 < 1479.26
    [s] = _setups([*LEAD, BREAK, RECLAIM, resumed, CONFIRM])
    assert (s.status, s.end_reason, s.ended_at_index) == (SetupStatus.INVALIDATED, "BREAK_RESUMED", 7)


def test_ages_out_after_the_expiry_bars() -> None:
    [s] = _setups([*LEAD, BREAK, RECLAIM, *[HOLD] * 13])
    assert (s.status, s.end_reason, s.ended_at_index) == (SetupStatus.EXPIRED, "AGED_OUT", 19)


def test_a_reclaim_after_the_entry_cutoff_is_not_taken() -> None:
    # Cutoff at the end of bar 5: the breakdown bar is on time, the reclaim bar 6 is not.
    assert _setups([*LEAD, BREAK, RECLAIM], cutoff_minutes=345) == []


def test_breakdown_bar_after_the_cutoff_is_ignored() -> None:
    assert _setups(SEQ, cutoff_minutes=355) == []


def test_levels_stop_at_break_low_and_target_from_the_shared_ladder() -> None:
    ctx = _ctx(SEQ)
    [s] = detect_failed_breakdown(ctx)[0]
    lv = trade_levels(s, ctx, [])
    assert lv is not None
    # Entry = confirmation close 1482; stop 1476 x 0.9995 = 1475.262; risk 6.738.
    # Ladder: SESSION_HIGH / OR_HIGH 1493 give 1.63R (< 2); PDH 1510 gives 28 / 6.738 = 4.16R.
    assert (lv.entry, lv.stop, lv.risk_per_share) == (D("1482"), D("1475.262"), D("6.738"))
    assert (lv.target, lv.target_source, lv.rr_below_min) == (D("1510"), "PDH", False)


def test_deterministic() -> None:
    a, b = detect_failed_breakdown(_ctx(SEQ)), detect_failed_breakdown(_ctx(SEQ))
    assert a == b


@pytest.mark.parametrize("rows", [SEQ[:5], [*LEAD, BREAK]])
def test_nothing_before_a_reclaim_closes(rows: list[Row]) -> None:
    assert _setups(rows) == []
