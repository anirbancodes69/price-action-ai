"""TV-SET-01..03 for BREAKOUT_RETEST anchored on PDH (TRD-04 §5). PDH 1500, pseudo-zone [1499.625, 1500.375]."""

from __future__ import annotations

from app.domain.setups.breakout_retest import detect_breakout_retest
from app.domain.setups.types import Setup, SetupStatus

from ._session import D, ctx_for, mk

LEAD = [
    ("1490", "1492", "1489", "1491"),
    ("1491", "1494", "1490", "1493"),
    ("1493", "1495", "1492", "1494"),
    ("1494", "1503", "1493", "1502"),  # 3: close 1502 > 1500.375 x 1.0005 = 1501.1252 -> breakout b
]


def pdh_setup(rows: list[tuple[str, str, str, str]]) -> Setup:
    setups, _ = detect_breakout_retest(ctx_for(mk(rows), pdh="1500", pdl="1400"))
    return next(s for s in setups if s.anchor == "PDH")


def test_tv_set_01_breakout_retest_confirmed() -> None:
    rows = [
        *LEAD,
        ("1502", "1504", "1502.5", "1503.5"),  # 4 (low above 1500.375 x 1.001 = 1500.875... no retest)
        ("1503.5", "1505", "1503", "1504"),  # 5
        ("1504", "1504.5", "1500.8", "1503"),  # 6 = b + 3: low 1500.8 <= 1500.875, close >= 1499.625
        ("1503", "1506", "1502.5", "1505.5"),  # 7: close > 1504.5 x 1.0005 = 1505.2523
    ]
    s = pdh_setup(rows)
    assert (s.breakout_index, s.retest_index, s.confirmed_at_index) == (3, 6, 7)
    assert (s.status, s.trigger_price, s.stop_base, s.confirm_close) == (
        SetupStatus.ENTRY_CONFIRMED,
        D("1504.5"),
        D("1499.625"),
        D("1505.5"),
    )
    assert s.retest_closes_hold is True


def test_retest_trigger_updates_to_latest_retest_bar() -> None:
    rows = [
        *LEAD,
        ("1502", "1504", "1500.8", "1503"),  # 4 retest: trigger 1504
        ("1503", "1505", "1500.5", "1504"),  # 5 retest again: trigger 1505, retest low 1500.5
    ]
    s = pdh_setup(rows)
    assert (s.status, s.trigger_price, s.stop_base) == (
        SetupStatus.AWAITING_CONFIRMATION,
        D("1505"),
        D("1499.625"),
    )


def test_tv_set_02_no_retest_expires_on_b_plus_7() -> None:
    far = ("1510", "1512", "1508", "1511")  # lows far above the zone: never a retest
    s = pdh_setup([*LEAD, *[far] * 6])  # bars 4..9 = b+1..b+6: still FORMING
    assert s.status is SetupStatus.FORMING
    s = pdh_setup([*LEAD, *[far] * 7])  # bar 10 = b+7
    assert (s.status, s.end_reason, s.ended_at_index) == (SetupStatus.EXPIRED, "NO_RETEST", 10)


def test_tv_set_03_close_below_zone_invalidates() -> None:
    s = pdh_setup([*LEAD, ("1502", "1502", "1498", "1498.8")])  # 1498.8 < 1499.625 x 0.9995 = 1499.1253
    assert (s.status, s.end_reason, s.ended_at_index) == (SetupStatus.INVALIDATED, "FAILED_BREAKOUT", 4)


def test_retest_close_below_zone_high_clears_hold_flag() -> None:
    s = pdh_setup([*LEAD, ("1502", "1502", "1499.8", "1500.0")])  # retest close 1500.0 < Z.high 1500.375
    assert s.retest_closes_hold is False
