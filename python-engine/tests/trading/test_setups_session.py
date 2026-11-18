"""TV-SET-04..07, 10, 13..17 for ORB and previous-day setups (TRD-04 §2-§4)."""

from __future__ import annotations

from app.domain.htf import HtfContext
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.prev_day import detect_prev_day
from app.domain.setups.types import SetupDirection, SetupStatus
from app.domain.types import BarState, StructureState

from ._session import D, ctx_for, flat_htf, mk

# TRD-04 §3 example: OR bars end 09:20/09:25/09:30 with highs 1494.0/1496.5/1495.0, lows 1486.0/1488.0/1489.5.
ORB_DAY = [
    ("1490", "1494.0", "1486.0", "1492"),  # 09:15-09:20
    ("1492", "1496.5", "1488.0", "1495"),  # 09:20-09:25
    ("1495", "1495.0", "1489.5", "1493"),  # 09:25-09:30 last OR bar -> detected here (index 2)
    ("1493", "1496", "1491", "1495"),  # 3
    ("1495", "1497", "1494", "1496"),  # 4
    ("1496", "1497", "1495", "1496.4"),  # 5
    ("1496.4", "1498.5", "1496", "1498.10"),  # 6 09:45 close 1498.10 > 1496.5 x 1.0005 = 1497.25
]


def test_tv_set_04_orb_worked_example() -> None:
    ctx = ctx_for(mk(ORB_DAY))
    setups, reasons = detect_opening_range(ctx)
    long = next(s for s in setups if s.direction is SetupDirection.LONG)
    assert reasons == []
    assert (long.detected_at_index, long.trigger_price, long.stop_base) == (2, D("1496.5"), D("1486.0"))
    assert (long.status, long.confirmed_at_index, long.confirm_close) == (
        SetupStatus.ENTRY_CONFIRMED,
        6,
        D("1498.10"),
    )
    assert long.width_pct is not None and round(long.width_pct, 2) == D("0.71")


def test_tv_set_17_opening_range_incomplete() -> None:
    assert detect_opening_range(ctx_for(mk(ORB_DAY[:2]))) == ([], [])  # 09:25 close


def _orb(width_high: str) -> list[tuple[str, str, str, str]]:
    """OR with low 1000 and a high giving the requested width (rows: 3 bars, then one quiet bar)."""
    return [("1000", width_high, "1000", "1000.5")] * 3 + [("1000.5", "1001", "1000", "1000.5")]


def test_tv_set_05_width_gate_boundaries() -> None:
    cases = [("1002.9", "OR_TOO_NARROW"), ("1003.0", None), ("1020.0", None), ("1020.1", "OR_TOO_WIDE")]
    for high, reason in cases:
        setups, reasons = detect_opening_range(
            ctx_for(mk(_orb(high)), htf=flat_htf(4, StructureState.SIDEWAYS))
        )
        if reason:
            assert (setups, reasons) == ([], [reason]), high
        else:
            assert reasons == [] and len(setups) == 2, high  # LONG and the SHORT mirror


def test_tv_set_06_close_below_or_low_invalidates() -> None:
    rows = [*ORB_DAY[:3], ("1493", "1493", "1480", "1485.0")]  # 1485.0 < 1486 x 0.9995 = 1485.257
    long = next(s for s in detect_opening_range(ctx_for(mk(rows)))[0] if s.direction is SetupDirection.LONG)
    assert (long.status, long.end_reason, long.ended_at_index) == (
        SetupStatus.INVALIDATED,
        "OR_LOW_BROKEN",
        3,
    )


def test_tv_set_07_age_12_open_13_expired() -> None:
    quiet = ("1494", "1495", "1493", "1494")  # inside the range, no trigger, no invalidation
    rows = [*ORB_DAY[:3], *[quiet] * 12]  # last bar index 14 = detected (2) + 12
    long = next(s for s in detect_opening_range(ctx_for(mk(rows)))[0] if s.direction is SetupDirection.LONG)
    assert long.status is SetupStatus.AWAITING_CONFIRMATION
    rows.append(quiet)  # index 15 = age 13
    long = next(s for s in detect_opening_range(ctx_for(mk(rows)))[0] if s.direction is SetupDirection.LONG)
    assert (long.status, long.end_reason) == (SetupStatus.EXPIRED, "AGED_OUT")


def test_tv_set_15_htf_turns_bearish() -> None:
    bars = mk([*ORB_DAY[:3], ("1493", "1495", "1491", "1494")])
    bear = BarState(StructureState.BEARISH, None, None, None)
    htf = [*flat_htf(3), HtfContext(0, bear)]
    long = next(
        s for s in detect_opening_range(ctx_for(bars, htf=htf))[0] if s.direction is SetupDirection.LONG
    )
    assert (long.status, long.end_reason) == (SetupStatus.INVALIDATED, "HTF_AGAINST")


def test_tv_set_16_cutoff_expires_and_blocks_confirmation() -> None:
    # cutoff at the end of bar 3; bar 4 ends after it, so even a breakout close there cannot confirm
    bars = mk([*ORB_DAY[:3], ("1493", "1495", "1491", "1494"), ("1494", "1499", "1494", "1498.5")])
    cutoff_minutes = 375 - 5 * 4  # session close - end of bar 3 (09:15 + 20 min)
    ctx = ctx_for(bars, cutoff_minutes=cutoff_minutes)
    long = next(s for s in detect_opening_range(ctx)[0] if s.direction is SetupDirection.LONG)
    assert (long.status, long.end_reason, long.ended_at_index) == (SetupStatus.EXPIRED, "SESSION_CUTOFF", 4)


def test_tv_set_10_short_mirror_is_informational() -> None:
    rows = [*ORB_DAY[:3], ("1488", "1489", "1480", "1484.0")]  # < 1486 x 0.9995 = 1485.257
    short = next(
        s
        for s in detect_opening_range(ctx_for(mk(rows), htf=flat_htf(4, StructureState.BEARISH)))[0]
        if s.direction is SetupDirection.SHORT
    )
    assert short.informational and short.status is SetupStatus.ENTRY_CONFIRMED


def test_tv_set_13_opens_at_or_above_pdh() -> None:
    rows = [("1500", "1502", "1498", "1501")] * 3
    setups, reasons = detect_prev_day(ctx_for(mk(rows), pdh="1500", pdl="1400"))
    assert not [s for s in setups if s.direction is SetupDirection.LONG]
    assert "OPENED_ABOVE_LEVEL" in reasons


def test_tv_set_14_approach_and_confirm_same_bar() -> None:
    # PDH 1500; opens below; bar 1 closes 1501 > 1500 x 1.0005 = 1500.75 (and >= 1500 x 0.995)
    rows = [("1490", "1492", "1489", "1491"), ("1491", "1502", "1490", "1501")]
    [long] = [
        s
        for s in detect_prev_day(ctx_for(mk(rows), pdh="1500", pdl="1400"))[0]
        if s.direction is SetupDirection.LONG
    ]
    assert (long.detected_at_index, long.confirmed_at_index, long.status) == (
        1,
        1,
        SetupStatus.ENTRY_CONFIRMED,
    )
    # stop base: no confirmed session swing low yet -> the session low so far (1489)
    assert long.stop_base == D("1489")


def test_pdh_approach_then_confirm_and_pdl_mirror() -> None:
    rows = [
        ("1490", "1492", "1489", "1491"),
        ("1491", "1500.5", "1490", "1500.2"),
        ("1500", "1503", "1500", "1502"),
    ]
    long = next(
        s
        for s in detect_prev_day(ctx_for(mk(rows), pdh="1500", pdl="1400"))[0]
        if s.direction is SetupDirection.LONG
    )
    assert (long.detected_at_index, long.confirmed_at_index) == (1, 2)
    down = [
        ("1410", "1412", "1409", "1411"),
        ("1411", "1411", "1399", "1399.5"),
    ]  # < 1400 x 0.9995 = 1399.3? no
    s_ = [
        s
        for s in detect_prev_day(
            ctx_for(mk(down), pdh="1500", pdl="1400", htf=flat_htf(2, StructureState.BEARISH))
        )[0]
        if s.direction is SetupDirection.SHORT
    ]
    assert s_ and s_[0].informational
