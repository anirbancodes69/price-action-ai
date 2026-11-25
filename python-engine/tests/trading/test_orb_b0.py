"""E4/E7: the ORB B0 detector and levels (ruleset pa-intraday 0.6.0). Hand-built bars; no database."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.domain.levels import TradeLevels, trade_levels
from app.domain.params import RulesetParams
from app.domain.setups.orb_b0 import OrbB0Setup, UnsupportedOrbParameter, detect_orb_b0
from app.domain.setups.types import SetupDirection, SetupStatus, SetupType
from app.domain.types import StructureState
from app.rulesets import load_ruleset

from ._session import ctx_for, flat_htf, mk

D = Decimal
P6 = load_ruleset("pa-intraday", "0.6.0")
# OR high 1005, low 1000 (width 0.5 %). Trigger 1005 x 1.0005 = 1005.5025; whipsaw level 1000 x 0.9995 = 999.5.
OR3 = [
    ("1002", "1005", "1000", "1003"),
    ("1003", "1004", "1001", "1002"),
    ("1002", "1003", "1000.5", "1001"),
]
QUIET = ("1003", "1004", "1001", "1003")
BREAK = ("1003", "1007", "1002", "1006")  # close 1006 > 1005.5025
BELOW = ("1001", "1002", "998", "999")  # close 999 < 999.5


def _detect(rows: list[tuple[str, str, str, str]], params: RulesetParams = P6, **kw):  # type: ignore[no-untyped-def]
    ctx = ctx_for(mk(rows), params=params, **kw)
    return ctx, *detect_orb_b0(ctx)


def _p(**over: object) -> RulesetParams:
    return replace(P6, values={**P6.values, **over})


def test_first_close_above_the_buffered_high_confirms_a_long_with_the_wick_range() -> None:
    ctx, setups, reasons = _detect([*OR3, QUIET, BREAK])
    assert reasons == [] and len(setups) == 1
    s = setups[0]
    assert isinstance(s, OrbB0Setup)
    assert (s.type, s.direction, s.status) == (
        SetupType.OPENING_RANGE_BREAKOUT, SetupDirection.LONG, SetupStatus.ENTRY_CONFIRMED,
    )  # fmt: skip
    assert (s.range_high, s.range_low, s.trigger_price, s.stop_base) == (
        D("1005"),
        D("1000"),
        D("1005"),
        D("1000"),
    )
    assert (s.detected_at_index, s.confirmed_at_index, s.confirm_close) == (2, 4, D("1006"))
    assert ctx.t == 4


def test_a_close_at_exactly_the_buffered_level_is_not_a_breakout() -> None:
    _, setups, _ = _detect([*OR3, ("1003", "1007", "1002", "1005.5025")])
    assert setups[0].status is SetupStatus.AWAITING_CONFIRMATION


def test_there_is_never_a_short_setup_and_the_15m_context_does_not_filter() -> None:
    bearish = flat_htf(5, StructureState.BEARISH)
    _, setups, _ = _detect([*OR3, QUIET, BREAK], htf=bearish)
    assert [s.direction for s in setups] == [SetupDirection.LONG]
    assert setups[0].status is SetupStatus.ENTRY_CONFIRMED  # B0 has no context filter at any instant
    _, setups2, _ = _detect([*OR3, QUIET, ("1001", "1002", "990", "992")])
    assert [s.direction for s in setups2] == [SetupDirection.LONG]  # a breakdown is not mirrored


def test_a_close_below_the_whipsaw_level_before_the_breakout_invalidates_and_stays_invalidated() -> None:
    _, setups, _ = _detect([*OR3, BELOW, BREAK])
    assert (setups[0].status, setups[0].end_reason, setups[0].ended_at_index) == (
        SetupStatus.INVALIDATED, "OR_LOW_BROKEN", 3,
    )  # fmt: skip


def test_first_only_the_first_breakout_bar_is_the_breakout_and_later_bars_change_nothing() -> None:
    _, setups, _ = _detect([*OR3, BREAK, BELOW, ("1000", "1010", "999", "1009")])
    assert (setups[0].status, setups[0].confirmed_at_index) == (SetupStatus.ENTRY_CONFIRMED, 3)


def test_the_breakout_window_is_60_minutes_after_t_or() -> None:
    # t_OR = 09:30; the bar index 14 ends 10:30 (in the window), index 15 ends 10:35 (out).
    _, inside, _ = _detect(OR3 + [QUIET] * 11 + [BREAK])
    assert inside[0].confirmed_at_index == 14
    _, outside, _ = _detect(OR3 + [QUIET] * 12 + [BREAK])
    assert (outside[0].status, outside[0].end_reason) == (SetupStatus.EXPIRED, "AGED_OUT")
    wide = _p(**{"orb.breakout_window_minutes": 65})
    _, later, _ = _detect(OR3 + [QUIET] * 12 + [BREAK], wide)
    assert later[0].status is SetupStatus.ENTRY_CONFIRMED  # the window is read from the ruleset


def test_the_entry_cutoff_still_applies_when_it_is_earlier_than_the_window() -> None:
    _, setups, _ = _detect(OR3 + [QUIET] * 3 + [BREAK], cutoff_minutes=345)  # cutoff 09:45
    assert (setups[0].status, setups[0].end_reason) == (SetupStatus.EXPIRED, "SESSION_CUTOFF")


def test_the_range_is_silent_until_it_has_closed_then_data_defects_are_reported_not_repaired() -> None:
    assert _detect(OR3[:2])[1:] == ([], [])
    gap = mk([*OR3, QUIET, BREAK])
    ctx = ctx_for(gap[:1] + gap[2:], params=P6)  # the 09:20 bar is missing
    assert detect_orb_b0(ctx) == ([], ["OR_MISSING_BAR"])


@pytest.mark.parametrize(
    ("high", "reason"),
    [("1002.9", "OR_TOO_NARROW"), ("1020.1", "OR_TOO_WIDE"), ("1003", None), ("1020", None)],
)
def test_the_range_width_band_is_the_ruleset_value(high: str, reason: str | None) -> None:
    rows = [("1000", high, "1000", "1000.5")] * 3 + [("1000.5", "1001", "1000", "1000.5")]
    _, setups, reasons = _detect(rows)
    assert (reasons == [reason]) if reason else (reasons == [] and len(setups) == 1)


@pytest.mark.parametrize(
    "override",
    [
        {"orb.range_basis": "BODY"},
        {"orb.requalify": "FIRST_PASSING"},
        {"orb.stop_method": "S-B"},
        {"orb.target_method": "LADDER"},
        {"orb.target_k": 0},
        {"orb.breakout_window_minutes": 0},
    ],
)
def test_unsupported_or_invalid_values_are_rejected_not_defaulted(override: dict[str, object]) -> None:
    with pytest.raises(UnsupportedOrbParameter):
        _detect([*OR3, QUIET, BREAK], _p(**override))


def test_a_ruleset_without_the_orb_keys_fails_closed() -> None:
    with pytest.raises(KeyError):
        _detect([*OR3, QUIET, BREAK], load_ruleset("pa-intraday", "0.5.0"))


def test_no_look_ahead_a_prefix_gives_the_same_decision_as_the_full_day_up_to_that_bar() -> None:
    rows = [*OR3, QUIET, BREAK, BELOW, ("1000", "1100", "900", "901")]
    full = mk(rows)
    for t in range(2, len(rows)):
        got = detect_orb_b0(ctx_for(full[: t + 1], params=P6))[0]
        again = detect_orb_b0(ctx_for(full[: t + 1], params=P6))[0]
        assert got == again  # deterministic
        if got and got[0].confirmed_at_index is not None:
            assert got[0].confirmed_at_index <= t
    assert (
        detect_orb_b0(ctx_for(full[:4], params=P6))[0][0].status is SetupStatus.AWAITING_CONFIRMATION
    )  # before 09:35
    assert detect_orb_b0(ctx_for(full[:5], params=P6))[0][0].status is SetupStatus.ENTRY_CONFIRMED
    # Bars after the breakout never change the confirmed setup.
    assert detect_orb_b0(ctx_for(full[:5], params=P6))[0] == detect_orb_b0(ctx_for(full, params=P6))[0]


# --- levels: stop S-A and FIXED_R target (2R, not 2x the range width) ----------------------------------------------


def _levels(tick: str | None, confirm_close: str = "1006", params: RulesetParams = P6) -> TradeLevels:
    rows = [*OR3, QUIET, ("1003", "1007", "1002", confirm_close)]
    ctx = ctx_for(mk(rows), params=params)
    ctx = replace(ctx, tick=D(tick) if tick else None)
    s = detect_orb_b0(ctx)[0][0]
    lv = trade_levels(s, ctx, [])
    assert lv is not None
    return lv


def test_levels_are_stop_below_the_range_low_and_a_target_of_exactly_two_r() -> None:
    lv = _levels("0.05")
    assert (lv.entry, lv.stop) == (D("1006"), D("999.50"))  # 1000 x (1 - 0.05 %) rounded down
    assert lv.risk_per_share == D("6.50") and lv.target == D("1019.00") and lv.target_source == "FIXED_R"
    assert lv.rr == D(2) and lv.rr_below_min is False
    assert lv.target - lv.entry != 2 * (D("1005") - D("1000"))  # two R, not twice the range width


def test_the_target_is_rounded_down_and_no_ladder_candidate_can_replace_it() -> None:
    lv = _levels("0.05", "1006.03")
    assert (lv.stop, lv.risk_per_share) == (D("999.50"), D("6.53"))
    assert lv.target == D("1019.05")  # 1006.03 + 13.06 = 1019.09 rounded down to 1019.05
    assert lv.target_source == "FIXED_R"


def test_without_a_tick_nothing_is_rounded() -> None:
    lv = _levels(None, "1006.03")
    assert (lv.stop, lv.target) == (D("999.5000"), D("1019.0900"))


def test_the_nominal_multiple_not_the_rounded_target_is_tested_against_min_rr() -> None:
    assert _levels("0.05", params=_p(**{"orb.target_k": 1.5})).rr_below_min is True
    assert (
        _levels("0.05", "1006.03").rr_below_min is False
    )  # rounding pulls rr under 2.0 slightly: not a failure
