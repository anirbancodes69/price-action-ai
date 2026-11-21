"""Strategy 01 Stage 3 tests (process §4): anchors, boundaries, lifecycle, data, replay and risk limits.

Complements `test_setups_sweep.py` (TV-SET-19..28). Fixtures reuse its `LEAD` and `SAME_BAR` bars; every
expected value is hand-computed. `pa-intraday 0.3.0`-equal rules apply (sbuf = bb = sb = 0.05%).
Level Y = PDL 1480: Y x (1 - sbuf) = 1479.26; sweep low 1478: stop base 1478.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from app.domain.analyse import analyse
from app.domain.levels import trade_levels
from app.domain.risk.validation import validate_stop
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep
from app.domain.setups.types import Setup, SetupContext, SetupStatus
from app.domain.snapshot import SnapshotStatus
from app.domain.types import PivotKind, SwingPoint
from app.domain.zone_cache import ZoneCache
from app.domain.zones import Zone, ZoneStatus
from app.rulesets import load_ruleset

from ._session import CLOSE, OPEN, D, ctx_for, mk
from .test_setups_sweep import LEAD, SAME_BAR, SWEEP

Row = tuple[str, str, str, str]
NOLEVEL: dict[str, object] = {"pdh": None, "pdl": None}

# A day with no PDL; opening range bars 0-2 (OR low 1517), broken by the close of bar 3 (1512 < 1516.2415).
TOP: list[Row] = [
    ("1530", "1532", "1520", "1525"),  # 0
    ("1525", "1527", "1518", "1520"),  # 1
    ("1520", "1522", "1517", "1518"),  # 2  OR low 1517
    ("1518", "1519", "1510", "1512"),  # 3
]


def _ctx(rows: list[Row], **kw: object) -> SetupContext:
    kw.setdefault("pdh", "1510")
    kw.setdefault("pdl", "1480")
    kw.setdefault("params", SWEEP)
    return ctx_for(mk(rows), **kw)  # type: ignore[arg-type]


def _setups(rows: list[Row], **kw: object) -> list[Setup]:
    return detect_liquidity_sweep(_ctx(rows, **kw))[0]


# ---------------------------------------------------------------------------------------------- anchors


def test_anchor_or_low() -> None:
    rows = [*LEAD[:3], ("1488", "1490", "1485", "1488.5"), ("1488.5", "1492", "1488", "1491")]
    # OR low 1487; bar 3: L 1485 < 1486.2565, C 1488.5 >= 1487; trigger H 1490; bar 4 closes 1491 > 1490.745.
    [s] = _setups(rows, **NOLEVEL)
    assert (s.anchor, s.swept_level, s.detected_at_index, s.sweep_low) == ("OR_LOW", D("1487"), 3, D("1485"))
    assert (s.status, s.confirmed_at_index) == (SetupStatus.ENTRY_CONFIRMED, 4)


SWING: list[Row] = [
    *TOP,
    ("1512", "1513", "1500", "1505"),  # 4  pivot low 1500 (confirmed on bar 6)
    ("1505", "1510", "1503", "1508"),  # 5
    ("1508", "1512", "1506", "1510"),  # 6
    ("1510", "1511", "1498", "1501"),  # 7  L 1498 < 1499.25, C 1501 >= 1500
    ("1501", "1515", "1500", "1513"),  # 8  1513 > 1511 x 1.0005 = 1511.5555
]


def test_anchor_swing_low_5m() -> None:
    [s] = _setups(SWING, **NOLEVEL)
    assert (s.anchor, s.swept_level, s.detected_at_index, s.sweep_low) == (
        "SWING_LOW_5M",
        D("1500"),
        7,
        D("1498"),
    )
    assert (s.trigger_price, s.status, s.confirmed_at_index) == (D("1511"), SetupStatus.ENTRY_CONFIRMED, 8)


def test_anchor_equal_lows_and_the_tie_with_a_swing_low_at_the_same_price() -> None:
    # Second 5m pivot low 1499.5 on bar 8 (0.033% below 1500, within 0.1%): pool level = min = 1499.5.
    day: list[Row] = [
        *SWING[:7],
        ("1510", "1512", "1507", "1509"),  # 7
        ("1509", "1510", "1499.5", "1503"),  # 8  pivot low 1499.5 (confirmed on bar 10)
        ("1503", "1506", "1501", "1504"),  # 9
        ("1504", "1507", "1502", "1506"),  # 10
        (
            "1503",
            "1504",
            "1497",
            "1499.8",
        ),  # 11 L 1497 < 1498.75; C 1499.8 >= 1499.5; < 1500 (not the swing low)
    ]
    ctx = _ctx(day, **NOLEVEL)
    [s] = detect_liquidity_sweep(ctx)[0]
    assert (s.anchor, s.swept_level, s.detected_at_index) == ("EQUAL_LOWS", D("1499.5"), 11)
    assert s.status is SetupStatus.AWAITING_CONFIRMATION


def test_tie_between_equal_lows_and_swing_low_at_the_same_price_takes_the_anchor_order() -> None:
    # Second pivot 1500.4 (0.027% above): pool level = min = 1500 = the swing low. Same price, two anchors.
    day: list[Row] = [
        *SWING[:7],
        ("1510", "1512", "1507", "1509"),  # 7
        ("1509", "1510", "1500.4", "1503"),  # 8  pivot low 1500.4 (confirmed on bar 10)
        ("1503", "1506", "1501", "1504"),  # 9
        ("1504", "1507", "1502", "1506"),  # 10
        (
            "1503",
            "1504",
            "1497",
            "1500.2",
        ),  # 11 L 1497 < 1499.25, C 1500.2 >= 1500, < 1500.4 (the 2nd swing low)
    ]
    got = _setups(day, **NOLEVEL)
    # One setup per sweep bar; anchor order puts EQUAL_LOWS before SWING_LOW_5M.
    assert [(s.anchor, s.swept_level, s.detected_at_index) for s in got] == [("EQUAL_LOWS", D("1500"), 11)]
    # OBSERVED (page §26 G-3): a later sweep of the same price is a second setup through the other anchor,
    # because a level is used once per (anchor, price), not once per price.
    more = _setups([*day, ("1500.2", "1502", "1496", "1500.2")], **NOLEVEL)
    assert [(s.anchor, s.detected_at_index) for s in more] == [("EQUAL_LOWS", 11), ("SWING_LOW_5M", 12)]


ZDAY: list[Row] = [
    *TOP,
    ("1512", "1513", "1505", "1508"),  # 4
    ("1508", "1510", "1504", "1506"),  # 5  close 1506 > zone high 1503: the zone is SUPPORT at bar 5
    ("1506", "1507", "1498", "1501"),  # 6  L 1498 < 1499.25, C 1501 >= 1500
]


class _FakeZones(ZoneCache):
    def __init__(self, zones: list[Zone]) -> None:
        super().__init__()
        self._fixed = zones

    def zones(self, *args: object, **kw: object) -> list[Zone]:  # type: ignore[override]
        return self._fixed


def _zone(low: str, high: str, status: ZoneStatus = ZoneStatus.ACTIVE) -> Zone:
    return Zone(D(low), D(high), (), 0, status=status)


def test_anchor_zone_low_of_an_active_support_zone_only() -> None:
    ctx = replace(_ctx(ZDAY, **NOLEVEL), zone_cache=_FakeZones([_zone("1500", "1503")]))
    [s] = detect_liquidity_sweep(ctx)[0]
    assert (s.anchor, s.swept_level, s.detected_at_index, s.zone is not None) == ("ZONE", D("1500"), 6, True)
    # Not support (the close of bar 5, 1506, is inside the zone), not active: no level.
    inside = replace(_ctx(ZDAY, **NOLEVEL), zone_cache=_FakeZones([_zone("1500", "1507")]))
    assert detect_liquidity_sweep(inside)[0] == []
    broken = replace(
        _ctx(ZDAY, **NOLEVEL), zone_cache=_FakeZones([_zone("1500", "1503", ZoneStatus.BROKEN_FLIPPED)])
    )
    assert detect_liquidity_sweep(broken)[0] == []


def _pivot_15m(rows: list[Row], confirmed_bar: int) -> SwingPoint:
    bars = mk(rows)
    return SwingPoint(PivotKind.LOW, 0, D("1500"), bars[0].start, 0, bars[confirmed_bar].end)


def test_anchor_swing_low_15m_and_only_from_its_confirmation() -> None:
    ctx = _ctx(ZDAY, **NOLEVEL)
    known = replace(ctx, pivots_15m=[_pivot_15m(ZDAY, 2)])
    [s] = detect_liquidity_sweep(known)[0]
    assert (s.anchor, s.swept_level, s.detected_at_index) == ("SWING_LOW_15M", D("1500"), 6)
    # Confirmed by the 15m bar that ends with 5m bar 6 or later: it is not a level for sweep bar 6.
    late = replace(ctx, pivots_15m=[_pivot_15m(ZDAY, 6)])
    assert detect_liquidity_sweep(late)[0] == []


# ----------------------------------------------------------------------------------------- boundaries


def _row5(close: str, low: str = "1478") -> list[Row]:
    return [*LEAD, ("1482", "1483", low, close)]


def test_reclaim_close_at_the_level_is_a_same_bar_sweep_just_below_it_is_not() -> None:
    [s] = _setups(_row5("1480"))  # C = Y exactly
    assert (s.detected_at_index, s.same_bar_reclaim) == (5, True)
    assert _setups(_row5("1479.99")) == []  # needs bar 6 to reclaim; bar 6 has not closed


def test_two_bar_reclaim_limit_on_the_second_low_is_inclusive() -> None:
    base = [*LEAD, ("1482", "1483", "1478", "1479.5")]  # L[w] 1478: limit 1478 x 0.9995 = 1477.261
    [at] = _setups([*base, ("1479.5", "1484", "1477.261", "1481")])
    assert (at.detected_at_index, at.same_bar_reclaim, at.sweep_low) == (6, False, D("1477.261"))
    [below] = _setups([*base, ("1479.5", "1484", "1477.26", "1481")])
    assert (below.detected_at_index, below.same_bar_reclaim, below.sweep_low) == (6, True, D("1477.26"))


def test_confirmation_needs_a_close_strictly_above_the_trigger_buffer() -> None:
    # trigger 1483; 1483 x 1.0005 = 1483.7415
    at = [*SAME_BAR[:6], ("1481", "1483.7415", "1481", "1483.7415")]
    above = [*SAME_BAR[:6], ("1481", "1483.75", "1481", "1483.75")]
    [a] = _setups(at)
    [b] = _setups(above)
    assert a.status is SetupStatus.AWAITING_CONFIRMATION
    assert (b.status, b.confirmed_at_index) == (SetupStatus.ENTRY_CONFIRMED, 6)


def test_sweep_failed_needs_a_close_below_the_sweep_low_not_at_it() -> None:
    [at] = _setups([*SAME_BAR[:6], ("1481", "1481.5", "1477", "1478")])
    [below] = _setups([*SAME_BAR[:6], ("1481", "1481.5", "1477", "1477.99")])
    assert at.status is SetupStatus.AWAITING_CONFIRMATION
    assert (below.status, below.end_reason) == (SetupStatus.INVALIDATED, "SWEEP_FAILED")


def test_entry_cutoff_boundary() -> None:
    # Bar 5 ends 09:45 IST, which is 345 minutes before the 15:30 close.
    assert len(_setups(SAME_BAR, cutoff_minutes=345)) == 1
    assert _setups(SAME_BAR, cutoff_minutes=346) == []


# ------------------------------------------------------------------------------------------- lifecycle

WAIT: Row = ("1482", "1483", "1481", "1482")


def test_expiry_after_expiry_bars() -> None:
    day = [*SAME_BAR[:6], *[WAIT] * 12]  # bars 6..17: age 12 at bar 17
    [live] = _setups(day)
    assert live.status is SetupStatus.AWAITING_CONFIRMATION
    [dead] = _setups([*day, WAIT])  # bar 18: age 13 > 12
    assert (dead.status, dead.end_reason) == (SetupStatus.EXPIRED, "AGED_OUT")


def test_a_level_is_used_once_per_session() -> None:
    # Bar 7 sweeps and reclaims PDL again (C 1480.5 >= 1480) but (PDL, 1480) is taken; the swing low 1481 is not
    # reclaimed on that bar (C < 1481).
    rows = [*SAME_BAR, ("1485", "1486", "1477", "1480.5")]
    assert [(s.anchor, s.detected_at_index) for s in _setups(rows)] == [("PDL", 5)]


# ----------------------------------------------------------------------------------------------- data


def test_gap_open_below_pdl_is_a_sweep_of_pdl_on_the_first_session_bar() -> None:
    yesterday = mk(
        [("1495", "1496", "1494", "1495"), ("1495", "1496", "1494", "1495")], OPEN - timedelta(minutes=10)
    )
    today = mk([("1470", "1485", "1465", "1482"), ("1482", "1490", "1481", "1488")])
    ctx = ctx_for([*yesterday, *today], pdh="1510", pdl="1480", params=SWEEP)
    [s] = detect_liquidity_sweep(ctx)[0]
    assert (s.anchor, s.detected_at_index, s.sweep_low, s.trigger_price) == ("PDL", 2, D("1465"), D("1485"))


def test_previous_session_bars_never_form_a_setup_in_this_session() -> None:
    yesterday = mk(SAME_BAR, OPEN - timedelta(minutes=5 * len(SAME_BAR)))
    today = mk([("1490", "1492", "1488", "1491")] * 4)
    ctx = ctx_for([*yesterday, *today], pdh="1510", pdl="1470", params=SWEEP)
    assert detect_liquidity_sweep(ctx)[0] == []


def test_a_missing_candle_is_not_filled() -> None:
    gapped = mk(SAME_BAR)
    del gapped[4]  # a missing 5m bar: the detector sees the bars it is given and invents none
    ctx = ctx_for(gapped, pdh="1510", pdl="1480", params=SWEEP)
    for s in detect_liquidity_sweep(ctx)[0]:
        assert s.trigger_price == gapped[s.detected_at_index].high


def test_invalid_or_short_input_gives_no_signal() -> None:
    p = load_ruleset("pa-intraday", "0.3.0")
    b5 = mk(SAME_BAR)
    short = analyse(
        b5, b5, OPEN, None, p, session_close=CLOSE, detectors=[detect_liquidity_sweep], isolated=True
    )
    assert short.check.status is SnapshotStatus.INSUFFICIENT_HISTORY and short.signal is None
    dup = [*b5, b5[-1]]
    bad = analyse(
        dup, dup, OPEN, None, p, session_close=CLOSE, detectors=[detect_liquidity_sweep], isolated=True
    )
    assert bad.check.status is SnapshotStatus.INVALID_INPUT and bad.signal is None


# --------------------------------------------------------------------------------------------- replay


def test_bar_by_bar_replay_confirms_on_the_same_bars_as_a_single_full_run() -> None:
    """A fresh run at each bar (the live and replay path) sees the same confirmations as the full-day run."""
    rows = SAME_BAR
    full = {s.confirmed_at_index for s in _setups(rows) if s.confirmed_at_index is not None}
    seen = set()
    for k in range(len(rows)):
        for s in _setups(rows[: k + 1]):
            if s.confirmed_at_index == k:
                seen.add(k)
    assert seen == full == {6}


# -------------------------------------------------------------------------------- stop-distance limits


def _stop_errors(stop_base: str) -> list[str]:
    ctx = replace(_ctx(SAME_BAR), tick=D("0.05"))
    [s] = detect_liquidity_sweep(ctx)[0]
    lv = trade_levels(replace(s, stop_base=D(stop_base)), ctx, [])
    assert lv is not None
    return validate_stop(lv.entry, lv.stop, D("0.05"), D("0.15"), D("2.0"))


@pytest.mark.parametrize(
    ("stop_base", "stop", "errors"),
    [
        ("1478", "1477.25", []),  # 1478 x 0.9995 = 1477.261 rounds down to the 0.05 tick
        ("1483.5", "1482.75", []),  # distance 2.25 >= 1485 x 0.15% = 2.2275
        ("1483.6", "1482.85", ["STOP_TOO_TIGHT"]),  # distance 2.15 < 2.2275
        ("1456.2", "1455.45", []),  # distance 29.55 <= 1485 x 2% = 29.7
        ("1456", "1455.25", ["STOP_TOO_WIDE"]),  # distance 29.75 > 29.7
    ],
)
def test_structural_stop_is_tick_rounded_and_the_distance_limits_apply(
    stop_base: str, stop: str, errors: list[str]
) -> None:
    ctx = replace(_ctx(SAME_BAR), tick=D("0.05"))
    [s] = detect_liquidity_sweep(ctx)[0]
    lv = trade_levels(replace(s, stop_base=D(stop_base)), ctx, [])
    assert lv is not None and lv.stop == D(stop)
    assert _stop_errors(stop_base) == errors
